# 报价系统 · 懒猫 VNC 应用

将 `quote-desktop 1.0.0` 封装为可通过浏览器访问的懒猫 VNC 应用。
支持 **Linux amd64 / x86_64**，要求 **lzcos >= 1.6.0**。

- 报价数据、仪器附件和导出文件持久化。
- XFCE 桌面启动时自动打开报价系统。
- `background_task: true` 防止平台主动休眠。
- LPK 仅包含配置和图标，**不内嵌 Docker 镜像**。

## 打包与安装

需要 `lzc-cli`（已使用 2.0.9 构建）。仅打包 LPK 不需要原应用压缩包或本地 Docker 镜像。

```sh
mkdir -p dist
lzc-cli project build -o dist/cloud.lazycat.app.quote-desktop-1.0.0.lpk
python3 tests/check_lpk.py dist/cloud.lazycat.app.quote-desktop-1.0.0.lpk
lzc-cli lpk install dist/cloud.lazycat.app.quote-desktop-1.0.0.lpk
```

安装时拉取以下镜像；若仓库为私有，目标微服需要配置拉取凭据：

```text
crpi-kyqfans5x5yi0xen.cn-hangzhou.personal.cr.aliyuncs.com/lonng_image/liunx_lpk:1.0.0
```

## 持久化与自启动

每位用户独立桌面，数据按平台注入的 `LAZYCAT_APP_DEPLOY_UID` 保存：

```text
/lzcapp/var/users/<部署UID>/
├── quote-desktop/
│   ├── quote-data.json   # 报价、库存、历史和设置
│   └── files/            # 仪器附件
├── exports/              # PDF、PNG、JSON 备份
├── quote.lock
└── startup.log
```

使用桌面上的「报价导出（持久保存）」目录保存文件。Documents、Downloads 也指向此目录；其他容器目录不保证持久化。备份整个用户目录才能包含附件，应用内 JSON 备份不能替代完整备份。

不挂载整个 HOME，避免覆盖镜像里的自启动配置。`run_as: "1000:1000"` 用于持久目录权限映射。重建/升级应保持包 ID、部署 UID 和数据目录不变；卸载时清理数据会删除持久内容。

**桌面会话自启动不等于已验证的微服开机自启动。** 安装后若平台提供开机启动开关，请开启并重启设备验证。UID 分目录也不代表已验证平台的文件系统安全隔离。

## 重新构建镜像（可选）

需要 Python 3、Docker，以及自行取得授权的原始 `release-linux.zip`。
准备脚本恢复并校验官方 Electron 33.4.11 runtime，仅修改主进程的数据路径和导出默认路径，其他业务文件保持不变。

```sh
python3 scripts/prepare.py /path/to/release-linux.zip
python3 -m unittest discover -s tests -v

docker build --platform linux/amd64 -t quote-desktop-vnc:1.0.0 images
IMAGE=crpi-kyqfans5x5yi0xen.cn-hangzhou.personal.cr.aliyuncs.com/lonng_image/liunx_lpk:1.0.0
docker tag quote-desktop-vnc:1.0.0 "$IMAGE"
# 先通过 docker login 登录自己的仓库；不要提交凭据。
docker push "$IMAGE"
```

更新镜像版本时同步修改 `lzc-manifest.yml`、`package.yml` 和 `tests/check_lpk.py`。
基础镜像使用官方 `kasmweb/core-debian-bookworm:1.17.0`；教程中的基础镜像在初次构建时需要认证，故未采用。

## 验证

```sh
python3 -m unittest discover -s tests -v
bash -n images/start-quote.sh tests/runtime.sh
# 在原生 amd64 Docker 上验证，临时测试容器/卷会自动清理：
bash tests/runtime.sh quote-desktop-vnc:1.0.0
```

未准备原应用时，依赖 `images/vendor` 的两项测试会跳过。运行测试覆盖 VNC、XFCE 自启动、真实窗口、测试文件重建保留和 UID 目录选择。

CLI 构建仍有 lint 提示：`run_as` 字段识别、`application.depends_on` 弃用，以及商店要求的 locales/镜像域名。本项目用于自行安装，不是商店上架配置；`run_as` 权限映射仍需设备端确认。

已验证镜像与 LPK 构建、VNC HTTP/WebSocket、自启动脚本执行及测试文件持久化。**本机 ARM/QEMU 下 Electron 因内存不足未能显示真实窗口**，尚未完成微服端业务验收。原生 amd64 设备上仍需验证：

1. 报价窗口自动出现。
2. 新建数据、导入附件、导出中文 PDF/PNG。
3. 重启应用后数据、附件和导出文件仍可用。
4. 不同用户数据隔离及设备重启后自动启动。

## 项目结构

```text
lzc-build.yml / lzc-manifest.yml / package.yml  # 懒猫打包配置
lzc-icon.png                                  # 应用图标
images/                                       # Dockerfile、VNC 与启动配置
scripts/prepare.py                            # 恢复 runtime、应用持久化补丁
tests/                                        # 准备、LPK 与运行测试
```

生成文件、原应用、下载缓存、日志和 LPK 均已忽略，不应提交源码仓库；LPK 可单独作为 GitHub Release 附件发布。

## 安全与授权

- VNC 6901 禁用内部认证，必须通过懒猫鉴权入口访问，不要直接公开该端口。
- Electron 以非 root、`--no-sandbox` 运行；此封装不构成完整安全审计，Electron 33 已旧。
- 原软件声明 `UNLICENSED`。本仓库不包含原应用及 Electron 二进制；图标来自原应用，公开图标、镜像或安装包前请确认授权。本项目不替上游授予开源许可。

参考：[官方 VNC 教程](https://developer.lazycat.cloud/app-vnc.html)、[构建规范](https://developer.lazycat.cloud/spec/build.html)、[文件持久化](https://developer.lazycat.cloud/advanced-file.html)。
