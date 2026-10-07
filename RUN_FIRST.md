# 可运行项目包

## Windows 一键运行

双击 `RUN.bat`，或在 PowerShell 中执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\RUN.ps1
```

脚本会创建本地 `.venv`、安装第三节课依赖、运行全量测试、执行编译检查，并运行检索对比实验。默认使用本地 Mock/确定性实现，不需要 GitHub Token 或模型 API Key。

## 手动运行

```powershell
py -m pip install -r requirements-lesson3.txt
py -m pytest -q
py -m compileall -q packages integrations experiments tests
py -m experiments.retrieval_comparison
```

需要真实 GitHub PR 时，再按 `.env.example` 配置凭据；本地课程验证不依赖外部服务。
