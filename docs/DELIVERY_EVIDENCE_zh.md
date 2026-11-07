# 交付 E：GitHub 仓库与干净 clone 重现证据

> **状态：待第五阶段执行完成后填入真实值。** 本文件刻意先留骨架，避免在 `git push` 与全新 clone 真正发生之前编造 URL、SHA 或测试结果。若本文件仍显示「待填」，即代表该交付项**未完成**。

| 项目 | 结果 |
|---|---|
| repo URL | 待填 |
| visibility | 待填（预设 private） |
| branch | 待填（预设 main） |
| commit SHA | 待填 |
| `gh repo view` 核对 | 待填 |
| `git remote -v` | 待填 |
| `git ls-remote origin refs/heads/main` 与本机 `git rev-parse HEAD` 比对 | 待填 |
| 全新 clone 目录 | 待填 |
| clone 后建环境 | 待填 |
| clone 后 `run_demo.py` 结果 | 待填 |
| clone 后 `pytest -q` 结果 | 待填 |
| 未完成范围 | 待填 |

执行依据：`docs/GITHUB_DELIVERY_zh.md`；推送前的 `.gitignore` 与 staged files 检查、账号核对（`CHANSingYeungSunny`）与仓库名可用性检查都需留存真实输出。
