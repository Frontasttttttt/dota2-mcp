using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using DotaOverlay.Wpf.Models;
using DotaOverlay.Wpf.Services;

namespace DotaOverlay.Wpf
{
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

        [DllImport("user32.dll")]
        private static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);

        private static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
        private const uint SWP_NOACTIVATE = 0x0010;
        private const uint SWP_SHOWWINDOW = 0x0040;

        private IntPtr _hwnd;
        private DotaStateService _stateService = new();
        private bool _isOverlayVisible = true;

        public MainWindow()
        {
            InitializeComponent();
            Closed += MainWindow_Closed;
        }

        protected override void OnSourceInitialized(EventArgs e)
        {
            base.OnSourceInitialized(e);
            _hwnd = new WindowInteropHelper(this).Handle;

            // Размещаем виджет в свободном месте монитора 2560x1080 (X=1680, Y=38)
            Left = 1680;
            Top = 38;
            Width = 850;
            Height = 65;

            // Настройка Click-Through (прозрачность для кликов)
            int exStyle = GetWindowLong(_hwnd, GWL_EXSTYLE);
            SetWindowLong(_hwnd, GWL_EXSTYLE, exStyle | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE);
            SetWindowPos(_hwnd, HWND_TOPMOST, 1680, 38, 850, 65, SWP_NOACTIVATE | SWP_SHOWWINDOW);

            // Регистрация глобальной горячей клавиши F8
            RegisterHotKey(_hwnd, HOTKEY_ID_F8, 0, VK_F8);

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
                _isOverlayVisible = !_isOverlayVisible;
                Visibility = _isOverlayVisible ? Visibility.Visible : Visibility.Collapsed;
                handled = true;
            }
            return IntPtr.Zero;
        }

        private void OnStateUpdated(BoardResponse? board)
        {
            Dispatcher.Invoke(() =>
            {
                UpdateUi(board);
            });
        }

        private void UpdateUi(BoardResponse? board)
        {
            if (board == null || !board.Ok)
            {
                return;
            }

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
