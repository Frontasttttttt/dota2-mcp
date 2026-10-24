using System;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using DotaOverlay.Wpf.Models;
using DotaOverlay.Wpf.Services;

namespace DotaOverlay.Wpf
{
    public enum OverlayMode
    {
        Auto,
        TimersOnly,
        DraftOnly,
        Hidden
    }

    public partial class MainWindow : Window
    {
        private const int GWL_EXSTYLE = -20;
        private const int WS_EX_TRANSPARENT = 0x00000020;
        private const int WS_EX_LAYERED = 0x00080000;
        private const int WS_EX_TOOLWINDOW = 0x00000080;
        private const int WS_EX_NOACTIVATE = 0x08000000;

        private const int WM_HOTKEY = 0x0312;
        private const int HOTKEY_ID_F8 = 9001;
        private const uint VK_F8 = 0x77;

        [DllImport("user32.dll", SetLastError = true)]
        private static extern int GetWindowLong(IntPtr hWnd, int nIndex);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern int SetWindowLong(IntPtr hWnd, int nIndex, int dwNewLong);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

        private IntPtr _hwnd;
        private DotaStateService _stateService = new();
        private OverlayMode _currentMode = OverlayMode.Auto;
        private BoardResponse? _lastBoard;

        public MainWindow()
        {
            InitializeComponent();
            Loaded += MainWindow_Loaded;
            Closed += MainWindow_Closed;
        }

        private void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            _hwnd = new WindowInteropHelper(this).Handle;

            // Настройка Click-Through (прозрачность для кликов мыши — клики летят в Доту)
            int exStyle = GetWindowLong(_hwnd, GWL_EXSTYLE);
            SetWindowLong(_hwnd, GWL_EXSTYLE, exStyle | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE);

            // Регистрация глобальной горячей клавиши F8
            RegisterHotKey(_hwnd, HOTKEY_ID_F8, 0, VK_F8);

            // Подключение хука сообщений окна для отлова F8
            var source = HwndSource.FromHwnd(_hwnd);
            source?.AddHook(HwndHook);

            // Запуск опроса GSI и Live Board
            _stateService.StateUpdated += OnStateUpdated;
            _stateService.Start();
        }

        private IntPtr HwndHook(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
        {
            if (msg == WM_HOTKEY && wParam.ToInt32() == HOTKEY_ID_F8)
            {
                CycleOverlayMode();
                handled = true;
            }
            return IntPtr.Zero;
        }

        private void CycleOverlayMode()
        {
            _currentMode = _currentMode switch
            {
                OverlayMode.Auto => OverlayMode.TimersOnly,
                OverlayMode.TimersOnly => OverlayMode.DraftOnly,
                OverlayMode.DraftOnly => OverlayMode.Hidden,
                OverlayMode.Hidden => OverlayMode.Auto,
                _ => OverlayMode.Auto
            };

            string modeTitle = _currentMode switch
            {
                OverlayMode.Auto => "Авто (Драфт при пиках, Таймеры в игре)",
                OverlayMode.TimersOnly => "Только таймеры рун и карты",
                OverlayMode.DraftOnly => "Только смурф-радар драфта",
                OverlayMode.Hidden => "Скрыт (нажми F8 для включения)",
                _ => "Авто"
            };

            ShowToast($"Режим оверлея: {modeTitle}");
            ApplyCurrentDisplayMode();
        }

        private async void ShowToast(string message)
        {
            ToastText.Text = message;
            NotificationToast.Visibility = Visibility.Visible;
            
            var fadeIn = new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(200));
            NotificationToast.BeginAnimation(OpacityProperty, fadeIn);

            await Task.Delay(2200);

            var fadeOut = new DoubleAnimation(1, 0, TimeSpan.FromMilliseconds(300));
            fadeOut.Completed += (s, e) => { NotificationToast.Visibility = Visibility.Collapsed; };
            NotificationToast.BeginAnimation(OpacityProperty, fadeOut);
        }

        private void OnStateUpdated(BoardResponse? board)
        {
            Dispatcher.Invoke(() =>
            {
                _lastBoard = board;
                UpdateUi(board);
            });
        }

        private void UpdateUi(BoardResponse? board)
        {
            if (board == null || !board.Ok)
            {
                TxtStatus.Text = " | Ожидание GSI / Меню";
                TxtStatus.Foreground = new SolidColorBrush(Color.FromRgb(110, 118, 129));
                ApplyVisibility(false, false);
                return;
            }

            string stage = board.Stage ?? "UNKNOWN";
            TxtStatus.Text = $" | {stage}";
            TxtStatus.Foreground = new SolidColorBrush(Color.FromRgb(45, 212, 191));

            // Обновление таймеров карты
            if (board.Timers != null)
            {
                int clock = (int)(board.Clock ?? 0);
                int absClock = Math.Abs(clock);
                string sign = clock < 0 ? "-" : "";
                TxtClock.Text = $"{sign}{absClock / 60:D2}:{absClock % 60:D2}";

                TxtRiverFmt.Text = board.Timers.RiverFmt;
                TxtLotusFmt.Text = board.Timers.LotusFmt;
                TxtBountyFmt.Text = board.Timers.BountyFmt;
                TxtWisdomFmt.Text = board.Timers.WisdomFmt;
                TxtRoshanFmt.Text = board.Timers.RoshanFmt;
                TxtRoshanTitle.Text = $"РОШАН: {(board.Timers.IsDay ? "ЮГ (СВЕТ)" : "СЕВЕР (ТЬМА)")}";
                IconRoshan.Text = board.Timers.IsDay ? "☀️" : "🌙";
                TxtTormentorFmt.Text = board.Timers.TormentorFmt;

                // Подсветка таймеров за 20 секунд до спавна
                HighlightTimer(BoxRiver, board.Timers.RiverSec <= 20, Color.FromRgb(56, 189, 248));
                HighlightTimer(BoxLotus, board.Timers.LotusSec <= 20, Color.FromRgb(244, 63, 94));
                HighlightTimer(BoxBounty, board.Timers.BountySec <= 20, Color.FromRgb(251, 191, 36));
                HighlightTimer(BoxWisdom, board.Timers.WisdomSec <= 25, Color.FromRgb(167, 139, 250));
            }

            // Обновление статуса байбека
            if (board.You != null)
            {
                if (board.You.HasBuyback)
                {
                    TxtBuybackStatus.Text = "ГОТОВ";
                    TxtBuybackStatus.Foreground = new SolidColorBrush(Color.FromRgb(16, 185, 129));
                    BoxBuyback.BorderBrush = new SolidColorBrush(Color.FromRgb(16, 185, 129));
                }
                else if (board.You.BuybackCooldown > 0)
                {
                    TxtBuybackStatus.Text = $"КД {board.You.BuybackCooldown}с";
                    TxtBuybackStatus.Foreground = new SolidColorBrush(Color.FromRgb(245, 158, 11));
                    BoxBuyback.BorderBrush = new SolidColorBrush(Color.FromRgb(245, 158, 11));
                }
                else
                {
                    TxtBuybackStatus.Text = $"НЕТ ЗОЛОТА ({board.You.BuybackCost})";
                    TxtBuybackStatus.Foreground = new SolidColorBrush(Color.FromRgb(239, 68, 68));
                    BoxBuyback.BorderBrush = new SolidColorBrush(Color.FromRgb(239, 68, 68));
                }
            }

            // Обновление смурф-радара драфта
            if (board.LobbyScout != null)
            {
                var rad = board.LobbyScout.Radiant ?? new();
                var dire = board.LobbyScout.Dire ?? new();

                ItemsRadiant.ItemsSource = rad;
                ItemsDire.ItemsSource = dire;

                TxtRadCount.Text = $" ({rad.Count}/5)";
                TxtDireCount.Text = $" ({dire.Count}/5)";

                // Поиск рекомендаций по банам среди противников
                var enemyBan = dire.FirstOrDefault(p => !string.IsNullOrEmpty(p.BanAdvice))?.BanAdvice;
                if (!string.IsNullOrEmpty(enemyBan))
                {
                    TxtBanAdvice.Text = enemyBan;
                }
                else
                {
                    TxtBanAdvice.Text = dire.Any(p => p.ThreatLevel == "danger")
                        ? "🚨 Обнаружен потенциальный смурф/бустер во вражеской команде!"
                        : "Сканирование лобби завершено. Критических аномалий не найдено.";
                }
            }

            ApplyCurrentDisplayMode();
        }

        private void HighlightTimer(System.Windows.Controls.Border border, bool isUrgent, Color alertColor)
        {
            if (isUrgent)
            {
                border.BorderBrush = new SolidColorBrush(alertColor);
                border.Background = new SolidColorBrush(Color.FromArgb(50, alertColor.R, alertColor.G, alertColor.B));
            }
            else
            {
                border.BorderBrush = new SolidColorBrush(Color.FromRgb(33, 38, 45));
                border.Background = new SolidColorBrush(Color.FromRgb(22, 27, 34));
            }
        }

        private void ApplyCurrentDisplayMode()
        {
            if (_lastBoard == null || !_lastBoard.Ok)
            {
                ApplyVisibility(false, false);
                return;
            }

            string stage = _lastBoard.Stage ?? "";

            switch (_currentMode)
            {
                case OverlayMode.Auto:
                    if (stage == "DOTA_GAMERULES_STATE_HERO_SELECTION")
                    {
                        ApplyVisibility(timers: false, draft: true);
                    }
                    else if (stage is "DOTA_GAMERULES_STATE_PRE_GAME" or "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS")
                    {
                        ApplyVisibility(timers: true, draft: false);
                    }
                    else
                    {
                        ApplyVisibility(timers: false, draft: false);
                    }
                    break;

                case OverlayMode.TimersOnly:
                    ApplyVisibility(timers: true, draft: false);
                    break;

                case OverlayMode.DraftOnly:
                    ApplyVisibility(timers: false, draft: true);
                    break;

                case OverlayMode.Hidden:
                    ApplyVisibility(timers: false, draft: false);
                    break;
            }
        }

        private void ApplyVisibility(bool timers, bool draft)
        {
            InGameTimersHud.Visibility = timers ? Visibility.Visible : Visibility.Collapsed;
            DraftRadarHud.Visibility = draft ? Visibility.Visible : Visibility.Collapsed;
        }

        private void MainWindow_Closed(object? sender, EventArgs e)
        {
            if (_hwnd != IntPtr.Zero)
            {
                UnregisterHotKey(_hwnd, HOTKEY_ID_F8);
            }
            _stateService.Dispose();
        }
    }
}
