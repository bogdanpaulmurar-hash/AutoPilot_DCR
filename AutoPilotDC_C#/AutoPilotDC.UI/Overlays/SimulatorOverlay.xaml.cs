// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// SimulatorOverlay.xaml.cs � Overlay vizual simulare (Faza 10)
// Autor: Bogdan Murar (Z003FU5C) - Siemens AG
// ============================================================

using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Shapes;
using AutoPilotDC.Models;

namespace AutoPilotDC.UI.Overlays;

public partial class SimulatorOverlay : Window
{
    // -- Constructor ---------------------------------------------------
    public SimulatorOverlay()
    {
        InitializeComponent();
        // Seteaza dimensiunea la ecran complet
        Left = 0;
        Top = 0;
        Width = SystemParameters.PrimaryScreenWidth;
        Height = SystemParameters.PrimaryScreenHeight;
    }

    // -- API publica ---------------------------------------------------

    /// <summary>
    /// Afiseaza cercul animat si tooltip-ul la coordonatele pasului.
    /// Apelat din SimulatorEngine.OnStepSimulating.
    /// </summary>
    public void ShowStep(StepModel step)
    {
        if (!Dispatcher.CheckAccess())
        {
            Dispatcher.Invoke(() => ShowStep(step));
            return;
        }

        double x = step.X;
        double y = step.Y;

        // Pozitioneaza cercul principal (PulseCircle � 40x40, centrat)
        Canvas.SetLeft(PulseCircle, x - 20);
        Canvas.SetTop(PulseCircle, y - 20);
        PulseCircle.Visibility = Visibility.Visible;

        // Pozitioneaza cercul interior (InnerCircle � 12x12, centrat)
        Canvas.SetLeft(InnerCircle, x - 6);
        Canvas.SetTop(InnerCircle, y - 6);
        InnerCircle.Visibility = Visibility.Visible;

        // Pozitioneaza tooltip-ul (offset 30px dreapta-jos)
        double tooltipX = x + 30;
        double tooltipY = y + 30;
        // Evita iesirea din ecran
        if (tooltipX + 290 > Width) tooltipX = x - 290;
        if (tooltipY + 80 > Height) tooltipY = y - 80;
        Canvas.SetLeft(TooltipBorder, tooltipX);
        Canvas.SetTop(TooltipBorder, tooltipY);

        // Completeaza textele tooltip
        TxtStepType.Text = step.StepType ?? "STEP";
        TxtDescription.Text = string.IsNullOrWhiteSpace(step.Description)
                              ? step.Comment ?? string.Empty
                              : step.Description;
        TxtCoords.Text = $"X={step.X}  Y={step.Y}";
        TxtDelay.Text = $"Delay: {step.DelayBefore:0.0}s";
        TooltipBorder.Visibility = Visibility.Visible;

        // Animatie pulse pe PulseCircle
        AnimatePulse();

        if (!IsVisible) ShowOverlay();
    }

    /// <summary>
    /// Ascunde toate elementele vizuale (intre pasi).
    /// </summary>
    public void HideStep()
    {
        if (!Dispatcher.CheckAccess())
        {
            Dispatcher.Invoke(HideStep);
            return;
        }

        PulseCircle.Visibility = Visibility.Collapsed;
        InnerCircle.Visibility = Visibility.Collapsed;
        TooltipBorder.Visibility = Visibility.Collapsed;
    }

    /// <summary>
    /// Afiseaza fereastra overlay.
    /// </summary>
    public void ShowOverlay()
    {
        if (!Dispatcher.CheckAccess())
        {
            Dispatcher.Invoke(ShowOverlay);
            return;
        }
        Show();
    }

    /// <summary>
    /// Ascunde fereastra overlay.
    /// </summary>
    public void HideOverlay()
    {
        if (!Dispatcher.CheckAccess())
        {
            Dispatcher.Invoke(HideOverlay);
            return;
        }
        HideStep();
        Hide();
    }

    // -- Animatie pulse ------------------------------------------------
    private void AnimatePulse()
    {
        // Scale 1 ? 1.5 ? 1 in 600ms, repeat 2x
        var scaleX = new DoubleAnimation(1.0, 1.5, TimeSpan.FromMilliseconds(300))
        {
            AutoReverse = true,
            RepeatBehavior = new RepeatBehavior(2)
        };
        var scaleY = new DoubleAnimation(1.0, 1.5, TimeSpan.FromMilliseconds(300))
        {
            AutoReverse = true,
            RepeatBehavior = new RepeatBehavior(2)
        };
        PulseScale.BeginAnimation(ScaleTransform.ScaleXProperty, scaleX);
        PulseScale.BeginAnimation(ScaleTransform.ScaleYProperty, scaleY);
    }
}