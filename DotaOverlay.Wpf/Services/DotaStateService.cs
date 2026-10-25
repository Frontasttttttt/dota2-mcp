using System;
using System.IO;
using System.IO.Pipes;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using DotaOverlay.Wpf.Models;

namespace DotaOverlay.Wpf.Services;

public sealed class DotaStateService : IDisposable
{
    private const string PipeName = "DotaOverlayPipe";
    private const string BoardUrl = "http://127.0.0.1:8081/api/board";

    private readonly HttpClient _client = new()
    {
        Timeout = TimeSpan.FromSeconds(2)
    };
    private readonly CancellationTokenSource _cts = new();
    private readonly JsonSerializerOptions _jsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };
    private Task? _workerTask;

    public event Action<BoardResponse?>? StateUpdated;
    public bool IsRunning { get; private set; }
    public bool IsUsingPipe { get; private set; }

    public void Start()
    {
        if (IsRunning) return;
        IsRunning = true;
        _workerTask = Task.Run(WorkerLoopAsync);
    }

    private async Task WorkerLoopAsync()
    {
        while (!_cts.Token.IsCancellationRequested)
        {
            // 1. Приоритетный транспорт: высокоскоростной Win32 Named Pipe (<1 мс задержка)
            bool pipeSuccess = await TryConsumePipeAsync(_cts.Token).ConfigureAwait(false);

            // 2. Резервный транспорт: опрос локального HTTP API при отсутствии Pipe
            if (!pipeSuccess && !_cts.Token.IsCancellationRequested)
            {
                IsUsingPipe = false;
                await PollHttpOnceAsync(_cts.Token).ConfigureAwait(false);

                try
                {
                    await Task.Delay(1000, _cts.Token).ConfigureAwait(false);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
            }
        }
    }

    private async Task<bool> TryConsumePipeAsync(CancellationToken ct)
    {
        try
        {
            using var pipe = new NamedPipeClientStream(".", PipeName, PipeDirection.In, PipeOptions.Asynchronous);
            // Быстрая попытка подключения к пайпу (таймаут 300 мс)
            await pipe.ConnectAsync(300, ct).ConfigureAwait(false);

            IsUsingPipe = true;
            using var reader = new StreamReader(pipe, Encoding.UTF8);

            while (!ct.IsCancellationRequested && pipe.IsConnected)
            {
                var line = await reader.ReadLineAsync(ct).ConfigureAwait(false);
                if (line is null)
                {
                    // Пайп закрыт сервером
                    break;
                }
                if (string.IsNullOrWhiteSpace(line)) continue;

                try
                {
                    var data = JsonSerializer.Deserialize<BoardResponse>(line, _jsonOptions);
                    StateUpdated?.Invoke(data);
                }
                catch
                {
                    // Игнорируем поврежденный пакет
                }
            }
            return true;
        }
        catch
        {
            // Пайп недоступен или сервер не запущен
            return false;
        }
    }

    private async Task PollHttpOnceAsync(CancellationToken ct)
    {
        try
        {
            var response = await _client.GetAsync(BoardUrl, ct).ConfigureAwait(false);
            if (response.IsSuccessStatusCode)
            {
                var json = await response.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
                var data = JsonSerializer.Deserialize<BoardResponse>(json, _jsonOptions);
                StateUpdated?.Invoke(data);
            }
            else
            {
                StateUpdated?.Invoke(null);
            }
        }
        catch
        {
            // Сервер оффлайн
            StateUpdated?.Invoke(null);
        }
    }

    public void Dispose()
    {
        _cts.Cancel();
        _client.Dispose();
        _cts.Dispose();
    }
}
