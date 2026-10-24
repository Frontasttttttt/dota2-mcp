using System;
using System.Net.Http;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using DotaOverlay.Wpf.Models;

namespace DotaOverlay.Wpf.Services
{
    public class DotaStateService : IDisposable
    {
        private readonly HttpClient _client;
        private readonly CancellationTokenSource _cts = new();
        private readonly string _boardUrl = "http://127.0.0.1:8081/api/board";
        private Task? _pollTask;

        public event Action<BoardResponse?>? StateUpdated;
        public bool IsRunning { get; private set; }

        public DotaStateService()
        {
            _client = new HttpClient
            {
                Timeout = TimeSpan.FromSeconds(2)
            };
        }

        public void Start()
        {
            if (IsRunning) return;
            IsRunning = true;
            _pollTask = Task.Run(PollLoopAsync);
        }

        private async Task PollLoopAsync()
        {
            using var timer = new PeriodicTimer(TimeSpan.FromMilliseconds(1000));
            while (!_cts.Token.IsCancellationRequested)
            {
                try
                {
                    var response = await _client.GetAsync(_boardUrl, _cts.Token);
                    if (response.IsSuccessStatusCode)
                    {
                        var json = await response.Content.ReadAsStringAsync(_cts.Token);
                        var data = JsonSerializer.Deserialize<BoardResponse>(json, new JsonSerializerOptions
                        {
                            PropertyNameCaseInsensitive = true
                        });
                        StateUpdated?.Invoke(data);
                    }
                    else
                    {
                        StateUpdated?.Invoke(null);
                    }
                }
                catch
                {
                    // Live HUD server is currently offline or unreachable
                    StateUpdated?.Invoke(null);
                }

                try
                {
                    await timer.WaitForNextTickAsync(_cts.Token);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
            }
        }

        public void Dispose()
        {
            _cts.Cancel();
            _client.Dispose();
            _cts.Dispose();
        }
    }
}
