using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Models;

namespace AutoPilotDC.Application;

public class RoutineService
{
    private readonly IRoutineRepository _repo;
    public RoutineService(IRoutineRepository repo) => _repo = repo;

    public IReadOnlyList<string> GetRoutineNames() => _repo.GetRoutineNames();
    public IReadOnlyList<string> GetNames() => _repo.GetRoutineNames();
    public RoutineFile? Load(string name) => _repo.Load(name);
    public void Save(RoutineFile routine) => _repo.Save(routine);
    public bool Delete(string name) => _repo.Delete(name);
    public bool Rename(string o, string n) => _repo.Rename(o, n);
    public bool Exists(string name) => _repo.Exists(name);
}