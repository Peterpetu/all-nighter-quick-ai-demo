# Commands for quick testing via Powershell

cd
## API Test Commands

### Get all tasks

```powershell
curl http://localhost:8000/tasks
```

### Create a new task

```powershell
curl -Method POST http://localhost:8000/tasks -Headers @{ "Content-Type" = "application/json" } -Body '{"title":"Test","description":"desc"}'
```

### Get a specific task (e.g., ID 999, expecting "Task not found" if it doesn't exist)

```powershell
curl http://localhost:8000/tasks/999
```

```powershell
curl -Method POST http://localhost:8000/chat -Headers @{ "Content-Type" = "application/json" } -Body '{"message":"Can you delete the car washing task completely?"}'
```