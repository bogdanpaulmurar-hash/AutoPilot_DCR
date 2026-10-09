// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// MainViewModel.cs � Faza 9: Adaugat LoginConfigCmd
// INSTRUCTIUNI: Integreaza aceste adaugiri in MainViewModel.cs existent
// Autor: Bogdan Murar (Z003FU5C) - Siemens AG
// ============================================================

// -- ADAUGARI IN MainViewModel.cs ---------------------------------
//
// 1. In sectiunea "// -- Commands --" adauga:
//    public ICommand LoginConfigCmd { get; }
//
// 2. In sectiunea "// -- State --" adauga:
//    private LoginConfig? _currentLoginConfig;
//    public LoginConfig? CurrentLoginConfig
//    {
//        get => _currentLoginConfig;
//        set { _currentLoginConfig = value; OnPropertyChanged(); }
//    }
//
// 3. In constructor, dupa initializarea celorlalte comenzi, adauga:
//    LoginConfigCmd = new RelayCommand(_ => OpenLoginConfig());
//
// 4. Adauga metoda privata:

/*
private void OpenLoginConfig()
{
    var dialog = new Views.Dialogs.LoginConfigDialog(CurrentLoginConfig);
    dialog.Owner = Application.Current.MainWindow;
    if (dialog.ShowDialog() == true && dialog.Result != null)
    {
        CurrentLoginConfig = dialog.Result;
        StatusText = CurrentLoginConfig.Enabled
            ? $"?? Login configurat: {CurrentLoginConfig.Mode}"
            : "?? Login dezactivat";
    }
}
*/

// 5. In SaveRoutine(), la crearea RoutineFile, adauga LoginConfig:
/*
var routine = new RoutineFile
{
    Name        = dialog.Result,
    Steps       = [.. Steps],
    LoginConfig = CurrentLoginConfig,   // <-- ADAUGAT Faza 9
    CreatedAt   = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
    ModifiedAt  = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
    Author      = "Bogdan Murar (Z003FU5C)"
};
*/

// 6. In LoadRoutine(), dupa incarcarea pasilor, adauga:
/*
CurrentLoginConfig = routine.LoginConfig;
*/

// 7. In PlayAsync call (metoda Play()), transmite LoginConfig:
/*
await _playerSvc.PlayAsync(Steps.ToList(), repeatCount, CurrentLoginConfig);
*/
