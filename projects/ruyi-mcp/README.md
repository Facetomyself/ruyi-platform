# ruyi-mcp：Firefox 自动化与调试控制面

平台在 `submodules/ruyi-mcp` 固定经过验收的源码版本；组件在独立仓库的 `linux` 分支提交与发布。版本看 [PINS](../../PINS.md#9-ruyi-mcp)，进度看 [STATUS](../../STATUS.yaml)，跨项目接口看 [架构](../../docs/01-architecture.md#5-ruyi-mcp-控制面与组件边界)。独立开发工作副本与平台锁定检出可以同时存在。

## 检出并验证

```bash
cd /var/lib/dsh/Ruyi/ruyi-platform
git submodule update --init --checkout -- submodules/ruyi-mcp
git submodule status -- submodules/ruyi-mcp
cd submodules/ruyi-mcp
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
npm ci
npm run check
```

`check` 验证 MCP 与实际 Python bridge、构建及协议测试，无需浏览器。部署依赖和真机验收见组件 [Linux 说明](../../submodules/ruyi-mcp/docs/linux-port.md)，容器阶段见 [Docker 设计](../../submodules/ruyi-mcp/docs/docker-design.md)。

## 跨仓更新顺序

1. 在组件仓 `linux` 分支提交、推送，并核对 CI 对应提交。
2. 在平台把 `submodules/ruyi-mcp` 切换到该明确提交；分支声明用于发现更新，平台日常检出使用固定 gitlink。
3. 同步 [PINS](../../PINS.md)、[STATUS](../../STATUS.yaml)、[变更日志](CHANGELOG.md) 及 [TIMELINE](../../TIMELINE.md) 的统计。若改变 Trace 接口，同步相应架构和验收记录。
4. 运行平台 `bash scripts/verify-pins.sh` 和组件 `npm run check` 后提交平台 pin。真实浏览器与 Trace 同会话另行运行并记录制品身份及报告。
