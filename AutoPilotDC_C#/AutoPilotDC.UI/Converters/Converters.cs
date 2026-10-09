// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// Converters.cs � Value converters pentru XAML bindings
// ============================================================

using System;
using System.Globalization;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;
using Color = System.Windows.Media.Color;
using Brush = System.Windows.Media.Brush;
using Brushes = System.Windows.Media.Brushes;

namespace AutoPilotDC.UI.Converters;

/// <summary>bool -> Visibility (true = Visible, false = Collapsed)</summary>
public class BoolToVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is true ? Visibility.Visible : Visibility.Collapsed;

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => value is Visibility.Visible;
}

/// <summary>bool -> Visibility inversat (true = Collapsed, false = Visible)</summary>
public class InverseBoolToVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is true ? Visibility.Collapsed : Visibility.Visible;

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => value is Visibility.Collapsed;
}

/// <summary>bool -> Brush (true = SuccessBrush, false = TextMutedBrush)</summary>
public class BoolToStatusBrushConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is true)
            return System.Windows.Application.Current.Resources["SuccessBrush"] as Brush
                ?? Brushes.LimeGreen;
            return System.Windows.Application.Current.Resources["TextMutedBrush"] as Brush
                ?? Brushes.Gray;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotImplementedException();
}

/// <summary>StepType string -> Brush (color per step type)</summary>
public class StepTypeToBrushConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        return (value as string) switch
        {
            "CLICK"      or "DBLCLICK" or "RIGHTCLICK" => new SolidColorBrush(Color.FromRgb(0, 153, 153)),
            "KEY"        or "TYPE"                      => new SolidColorBrush(Color.FromRgb(0, 212, 255)),
            "SCROLL"     or "MOVE"                      => new SolidColorBrush(Color.FromRgb(160, 160, 192)),
            "DELAY"                                     => new SolidColorBrush(Color.FromRgb(255, 179, 71)),
            "SCREENSHOT"                                => new SolidColorBrush(Color.FromRgb(0, 200, 150)),
            "QUESTION"                                  => new SolidColorBrush(Color.FromRgb(224, 82, 82)),
            string s when s.StartsWith("browser_")     => new SolidColorBrush(Color.FromRgb(100, 180, 255)),
            _                                           => new SolidColorBrush(Color.FromRgb(160, 160, 192)),
        };
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotImplementedException();
}

/// <summary>bool Skip -> Opacity (true = 0.4, false = 1.0)</summary>
public class SkipToOpacityConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is true ? 0.4 : 1.0;

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotImplementedException();
}

/// <summary>bool HasError -> Brush (true = RowErrorBrush, false = Transparent)</summary>
public class ErrorToBrushConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is true)
            return System.Windows.Application.Current.Resources["RowErrorBrush"] as Brush
                   ?? Brushes.DarkRed;
        return Brushes.Transparent;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotImplementedException();
}

/// <summary>int countdown -> string display (0 = "")</summary>
public class CountdownToStringConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is int i && i > 0 ? $"? {i}" : "";

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotImplementedException();
}
