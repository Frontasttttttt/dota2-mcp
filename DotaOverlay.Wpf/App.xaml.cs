using System;
using System.IO;
using System.Windows;

namespace DotaOverlay.Wpf;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        File.WriteAllText(@"c:\AI\overlay_startup.log", "OnStartup entered\n");

        AppDomain.CurrentDomain.UnhandledException += (s, ev) =>
        {
            try
            {
                File.AppendAllText(@"c:\AI\overlay_startup.log", "UnhandledException: " + ev.ExceptionObject.ToString() + "\n");
            }
            catch { }
        };

        DispatcherUnhandledException += (s, ev) =>
        {
            try
            {
                File.AppendAllText(@"c:\AI\overlay_startup.log", "DispatcherUnhandledException: " + ev.Exception.ToString() + "\n");
            }
            catch { }
        };

        try
        {
            File.AppendAllText(@"c:\AI\overlay_startup.log", "Creating MainWindow\n");
            var mainWindow = new MainWindow();
            MainWindow = mainWindow;
            File.AppendAllText(@"c:\AI\overlay_startup.log", "Showing MainWindow\n");
            mainWindow.Show();
            File.AppendAllText(@"c:\AI\overlay_startup.log", "MainWindow shown successfully\n");
        }
        catch (Exception ex)
        {
            File.AppendAllText(@"c:\AI\overlay_startup.log", "Exception creating MainWindow: " + ex.ToString() + "\n");
        }
    }
}
