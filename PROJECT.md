# ScreenOCR - 桌面截图 OCR 工具

## 持续进化目标

**使命：打造最好用的桌面 OCR 工具**

这不是一个一次性项目，而是一个**持续进化**的产品。就像 Archie 自身一样，ScreenOCR 需要不断改进、优化、完善。

### 进化原则

| 原则 | 说明 |
|------|------|
| **用户体验优先** | 每个功能都要让用户觉得"好用" |
| **持续改进** | 没有"完成"状态，永远有优化空间 |
| **主动发现问题** | 不等用户反馈，主动审查代码和体验 |
| **小步快跑** | 每次改进一点，持续迭代 |

### 铁律：portable 目录同步规则

**每次修改 `src/` 目录中的任何文件后，必须立即同步到 `portable/src/`**

```bash
# 同步命令（每次修改代码后必须执行）
cp -r D:/5118/Archie/projects/paddleocr/src/* D:/5118/Archie/projects/paddleocr/portable/src/
```

---

## GitHub 发布规则

**仓库地址**: https://github.com/4111y80y/paddleocr

### 代码提交规则

1. **只提交源代码**，不提交大文件：
   - `src/` - 源代码 (必须提交)
   - `portable/src/` - 便携版源代码副本 (必须提交)
   - `portable/ScreenOCR.bat` - 启动脚本 (必须提交)
   - `demo/` - 演示图片 (必须提交)
   - `README.md` - 项目说明 (必须提交)
   - `requirements_exact.txt` - 依赖列表 (必须提交)

2. **不要提交的内容** (已在 .gitignore 中配置)：
   - `portable/python/` - Python 环境 (1.6GB，太大)
   - `__pycache__/` - 编译缓存
   - `*.log` - 日志文件
   - `nuitka-crash-report.xml` - 构建日志

### 提交命令

```bash
cd D:/5118/Archie/projects/paddleocr

# 1. 查看修改了哪些文件
git status

# 2. 添加修改的文件（不要用 git add -A）
git add src/修改的文件.py portable/src/修改的文件.py

# 3. 提交并推送
git commit -m "fix: 修复xxx问题

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git push
```

### 发布 Release 规则

**何时发布 Release**：
- 重要功能完成
- 重大 bug 修复
- 用户请求发布新版本

**Release 发布命令**：

```bash
cd D:/5118/Archie/projects/paddleocr

# 1. 准备发布文件（不含 python 环境）
mkdir -p release_temp
cp -r portable/src portable/ScreenOCR.bat release_temp/

# 2. 创建 README
cat > release_temp/README_PORTABLE.txt << 'EOF'
ScreenOCR Portable Version
==========================

Usage:
1. Download and extract this package
2. Install Python 3.10+ and dependencies: pip install -r requirements_exact.txt
3. Run: python src/main.py

Or download the full portable version with Python environment from the author.
EOF

# 3. 打包
cd release_temp
powershell -Command "Compress-Archive -Path * -DestinationPath '../ScreenOCR-vX.X.X-portable.zip' -Force"
cd ..

# 4. 创建 Release
gh release create vX.X.X --title "ScreenOCR vX.X.X" --notes "
## ScreenOCR vX.X.X

### 更新内容
- 修复: xxx
- 新增: xxx

### 下载说明
- ScreenOCR-vX.X.X-portable.zip - 便携版源代码包
" ScreenOCR-vX.X.X-portable.zip

# 5. 清理临时文件
rm -rf release_temp ScreenOCR-vX.X.X-portable.zip
```

### 版本号规则

| 版本号 | 含义 |
|--------|------|
| v1.0.x | Bug 修复 |
| v1.x.0 | 新功能 |
| vX.0.0 | 重大更新 |

### 当前版本

- **v1.0.0** (2026-02-01): 首个正式版本
  - 截图识别、批量处理、置信度显示
  - 历史记录、编辑模式
  - 深色主题 UI

**检查清单**：
1. 修改了 `src/*.py` 文件？ -> 执行同步命令
2. 新增了 `src/` 下的文件？ -> 执行同步命令
3. 删除了 `src/` 下的文件？ -> 同时删除 `portable/src/` 对应文件

**验证方式**：
```bash
# 对比两个目录，确保一致
diff -rq D:/5118/Archie/projects/paddleocr/src D:/5118/Archie/projects/paddleocr/portable/src
```

**违反此规则的后果**：
用户使用 `portable/ScreenOCR.bat` 运行时会使用旧代码，导致修复无效。

### 进化检查清单（每轮空闲时执行）

```bash
# 1. 代码质量检查
wc -l src/*.py | sort -rn  # 文件不超过 500 行
grep -n "def \|class " src/*.py  # 方法不超过 50 行

# 2. 用户体验审查
# - 界面是否美观？
# - 操作是否流畅？
# - 文字是否清晰？
# - 有没有卡顿？

# 3. 功能完整性检查
# - 截图功能正常？
# - OCR 识别准确？
# - 复制功能正常？
# - 历史记录正常？
```

### 进化方向

**短期目标（当前 Phase）**：
- 界面美观、专业
- 操作流畅、无卡顿
- 中文界面完善

**中期目标**：
- 识别准确率提升
- 支持更多语言
- 表格识别优化
- 公式识别支持

**长期目标**：
- 成为 Windows 上最好用的 OCR 工具
- 超越现有商业软件的用户体验
- 开源社区认可

### 竞品对标

| 竞品 | 优点 | 我们要超越的点 |
|------|------|----------------|
| 天若 OCR | 轻量快速 | 界面更美观 |
| Snipaste | 截图体验好 | OCR 更准确 |
| 商业 OCR 软件 | 功能全 | 免费开源 + 离线使用 |

---

## 项目目标
打造一款**最佳桌面 OCR 工具**，发布为 **Portable 单文件 exe**，用户双击即可运行，无需安装任何依赖。

## 发布形式
**Portable 便携版** - 单个 exe 文件，用户下载后直接双击运行：
- 无需安装 Python
- 无需安装 CUDA
- 无需任何配置
- 首次运行自动下载 OCR 模型到用户目录

## 产品特性
1. **一键截图识别** - 快捷键触发，框选屏幕区域，自动 OCR
2. **实时预览** - 截图后立即显示识别结果
3. **智能复制** - 一键复制识别文字到剪贴板
4. **历史记录** - 保存最近的识别记录，方便回顾
5. **多语言支持** - 中文、英文、中英混合
6. **设备选择** - 用户可选择 CPU 或指定 GPU 进行推理
7. **系统托盘** - 最小化到托盘，随时待命
8. **Portable** - 单文件 exe，下载即用

## 设备选择功能
用户可在设置中选择推理设备：
- **CPU** - 无 GPU 或想节省显存时使用
- **GPU 0** - 第一块显卡 (默认)
- **GPU 1** - 第二块显卡 (如有)
- **GPU N** - 第 N 块显卡

### 技术实现
```python
import paddle

# 获取可用 GPU 列表
def get_available_devices():
    devices = [("CPU", "cpu")]
    if paddle.device.is_compiled_with_cuda():
        gpu_count = paddle.device.cuda.device_count()
        for i in range(gpu_count):
            name = paddle.device.cuda.get_device_name(i)
            devices.append((f"GPU {i}: {name}", f"gpu:{i}"))
    return devices

# 设置推理设备
def set_device(device_id):
    paddle.set_device(device_id)  # "cpu" 或 "gpu:0" 或 "gpu:1"

# PaddleOCR 初始化时指定设备
ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=True, gpu_id=0)
```

### UI 设计
- 主界面状态栏显示当前设备: `[GPU 0: NVIDIA RTX 4090]`
- 设置界面提供设备下拉选择框
- 切换设备后自动重新初始化 OCR 引擎

## 技术栈
- Python 3.10
- PaddlePaddle GPU + PaddleOCR
- **PySide6** (Qt 官方 Python 绑定，与 PyInstaller 兼容性更好)
- mss (高性能屏幕截图)
- Pillow (图像处理)
- mamba 环境: `PaddleOCR`

## 发布形式 (已确定，不再尝试 exe 打包)

**重要决定：放弃 PyInstaller/Nuitka 打包 exe 方案**

经过多次尝试，PyInstaller 打包 PySide6 + PaddleOCR 组合会出现 `DLL load failed` 错误，无法稳定解决。

**当前发布方式：便携版 Python 环境**

```
portable/
├── ScreenOCR.bat      # 用户双击此文件启动
├── python/            # 完整的 Python 环境（含所有依赖）
└── src/               # 源代码（与主 src/ 保持同步）
```

**用户使用流程**：
1. 解压 `ScreenOCR-portable.zip` 到任意位置
2. 双击 `ScreenOCR.bat` 运行
3. 按 `Ctrl+Shift+O` 截图识别

**这个方案已经可用，不需要再花时间在打包问题上。**

---

## 当前进化重点：功能和体验优化

**打包问题已解决，现在专注于让 ScreenOCR 成为最好用的 OCR 工具！**

进化体应该：
1. **不要再尝试 PyInstaller/Nuitka 打包** - 这条路已经证明走不通
2. **专注于功能进化** - 界面优化、用户体验、OCR 准确率
3. **每次修改后同步 portable/src/** - 确保用户能用到最新版本

---

## 打包经验教训 (重要)

### PyInstaller + Qt 打包失败总结

**问题**: `ImportError: DLL load failed while importing QtWidgets`

**尝试过的方案 (均失败)**:
1. `--onefile` 模式 - Qt DLL 无法正确加载
2. `--onedir` + `--collect-all PyQt6` - 仍然 DLL 错误
3. `--onedir` + `--collect-all PySide6` - 仍然 DLL 错误
4. 手动复制 Qt6*.dll 到 exe 目录 - 时好时坏，不稳定
5. Nuitka 打包 - 编译时间过长

**最终解决方案**:
放弃 PyInstaller，改用**便携版 Python 环境**：
1. 复制整个 mamba 环境到 `portable/python/`
2. 复制源代码到 `portable/src/`
3. 创建 `ScreenOCR.bat` 使用相对路径调用 Python

**结论**: PaddleOCR + PySide6 组合与 PyInstaller 兼容性差，便携版是更可靠的发布方式。

## GUI 设计规范
- **风格**: 现代简约，深色/浅色主题切换
- **主窗口**:
  - 顶部: 工具栏 (截图按钮、设置、历史)
  - 中部: 截图预览区 + 识别结果文本区 (左右分栏)
  - 底部: 状态栏 (识别耗时、GPU状态)
- **截图覆盖层**: 全屏半透明遮罩，鼠标框选区域
- **快捷键**:
  - `Ctrl+Shift+O` 全局截图快捷键
  - `Ctrl+C` 复制识别结果
  - `Esc` 取消截图

## 环境配置
```bash
mamba activate PaddleOCR
# 已安装: PaddlePaddle 2.6.2 + PaddleOCR 2.7.3

# 新增 GUI 依赖
pip install PyQt6 mss keyboard pyinstaller
```

## 项目结构
```
projects/paddleocr/
├── src/
│   ├── main.py              # 程序入口
│   ├── main_window.py       # 主窗口
│   ├── screenshot_overlay.py # 截图覆盖层
│   ├── ocr_engine.py        # OCR 引擎封装
│   ├── history_manager.py   # 历史记录管理
│   ├── settings.py          # 设置管理
│   └── resources/           # 图标、样式表
├── samples/                  # 测试样本
│   └── blood_report.png
├── dist/                     # 打包输出
├── PROJECT.md
└── requirements.txt
```

## 待办事项

### Phase 1: 核心功能 (已完成基础)
- [x] Task 1: 创建 mamba 环境，安装 PaddleOCR (2026-01-31)
- [x] Task 2: 验证 OCR 识别效果 (2026-01-31)
- [x] Task 3: 测试识别血常规报告单成功 (164个文本区域)

### Phase 2: GUI 框架 (已完成)
- [x] Task 6: 创建 PyQt6 主窗口框架 (2026-01-31)
  - 工具栏、状态栏、分栏布局
  - 深色主题 QSS 样式
  - 实现: main.py, main_window.py
- [x] Task 7: 实现截图覆盖层 (2026-01-31)
  - 全屏半透明遮罩
  - 鼠标拖拽框选区域
  - 实时显示选区尺寸
  - 实现: screenshot_overlay.py (含多屏幕支持)
- [x] Task 8: 集成 OCR 引擎 (2026-01-31)
  - 封装 PaddleOCR 调用
  - 异步识别避免界面卡顿 (QThread + OCRWorker)
  - 显示识别进度
  - 实现: ocr_engine.py

### Phase 3: 用户体验
- [x] Task 9: 实现全局快捷键 (Ctrl+Shift+O) (2026-01-31)
  - 使用 keyboard 库实现全局热键监听
  - 添加 GlobalHotkeyManager 类到 main.py
  - 热键信号通过 Qt 信号槽机制传递到主线程
  - 程序退出时自动清理热键注册
- [x] Task 10: 添加系统托盘图标和菜单 (2026-01-31)
  - 实现 SystemTrayManager 类到 main.py
  - 蓝色 OCR 图标 (32x32)
  - 托盘菜单: Screenshot、Show Window、Quit
  - 双击/单击激活显示主窗口
  - 关闭窗口时最小化到托盘而非退出
- [x] Task 11: 实现历史记录功能 (2026-01-31)
  - 创建 history_manager.py 模块
  - HistoryManager 类: 持久化存储、搜索、删除功能
  - HistoryRecord 数据类: id、timestamp、text、thumbnail、elapsed_time
  - HistoryDialog 对话框: 搜索、预览、复制、删除、恢复
  - OCR 完成后自动保存历史记录（含缩略图）
  - 历史记录保存到 %LOCALAPPDATA%/ScreenOCR/history.json
- [x] Task 12: 添加设置界面 (语言、快捷键、主题) (2026-01-31)
  - 创建 settings.py 设置管理模块 (AppSettings 数据类 + SettingsManager)
  - 创建 SettingsDialog 对话框 (语言、快捷键、主题、行为选项)
  - 集成到 MainWindow，设置保存到 %LOCALAPPDATA%/ScreenOCR/settings.json
  - OCR 引擎支持动态语言切换

### Phase 4: 便携版发布 (已完成)
- [x] Task 13: 便携版发布 (2026-01-31)
  - 放弃 PyInstaller/Nuitka（Qt DLL 兼容性问题无法解决）
  - 改用便携版 Python 环境方式
  - 输出: `portable/ScreenOCR.bat`
  - 用户解压后双击即可运行

### Phase 5: 界面优化和问题修复 (当前阶段)
- [x] Task 16: 界面文字改为默认中文
  - 当前问题: 即使选择中文，界面仍显示英文
  - 要求: 所有按钮、标签、提示文字默认显示中文
  - 涉及文件: main.py, main_window.py, screenshot_overlay.py, settings.py
  - 需要修改的文字:
    - "Screenshot (Ctrl+Shift+O)" -> "截图 (Ctrl+Shift+O)"
    - "Open Image" -> "打开图片"
    - "Device:" -> "设备:"
    - "History" -> "历史记录"
    - "Settings" -> "设置"
    - "[OCR Result]" -> "[识别结果]"
    - "Copy" -> "复制"
    - "[Screenshot Preview]" -> "[截图预览]"
    - "OCR result will appear here..." -> "识别结果将显示在这里..."

- [x] Task 17: 界面布局优化，解决不对齐和混乱问题 (2026-01-31)
  - 当前问题: 界面元素不对齐，看起来很乱
  - 要求:
    1. 工具栏按钮间距统一
    2. 左右分栏比例合理（如 1:1 或 2:3）
    3. 标签和控件对齐
    4. 状态栏信息排列整齐
    5. 整体视觉效果专业美观
  - 实现:
    - 工具栏: 添加统一样式表，spacing: 8px，按钮 padding: 6px 16px
    - 设备选择器: 使用容器布局，标签和控件对齐，统一高度 26px
    - 左右分栏: 设置 stretch factor 1:1，初始尺寸 500:500
    - 分栏手柄: 宽度 4px，添加 hover 效果
    - 截图预览: 添加标题头部，统一样式
    - 识别结果: 优化标题和复制按钮布局，固定按钮尺寸 80x28
    - 状态栏: 使用样式表统一风格，分隔符使用半透明白色
    - 设备状态: 格式改为 "设备: CPU" 更清晰

- [x] Task 18: 关闭窗口后控制台不自动关闭 (2026-01-31)
  - 当前问题: 关闭 GUI 窗口后，bat 启动的控制台窗口仍然存在
  - 修复方案: 修改 portable/ScreenOCR.bat，使用 `pythonw.exe` 代替 `python.exe`
  - 验证: 关闭 GUI 后不留下任何窗口

- [x] Task 19: 每次修改后同步 portable 目录 (2026-01-31)
  - 命令: `cp -r src/* portable/src/`
  - 这是铁律，每次修改代码后必须执行
  - 已执行同步，验证通过

### Phase 6: 功能增强和体验优化 (进行中)

- [x] Task 20: 添加识别结果置信度显示 (2026-01-31)
  - 在 OCR 结果中显示每个识别文本的置信度分数
  - 低置信度文本用不同颜色标记（如黄色/红色）
  - 在结果区域添加置信度阈值设置
  - 实现:
    - `ocr_engine.py`: 添加 `recognize_with_confidence()` 方法返回 (text, confidence) 列表
    - `main_window.py`:
      - 修改 `OCRWorker` 返回置信度数据
      - 增强 `ResultTextWidget` 支持置信度显示
      - 添加置信度阈值下拉选择 (50%-95%，默认80%)
      - 添加"显示置信度"开关按钮
      - 低置信度 (<80%) 黄色标记，极低 (<60%) 红色标记
      - 复制功能只复制纯文本（不含置信度标记）

- [x] Task 21: 实现表格识别模式 (2026-01-31)
  - 添加专门的表格识别功能
  - 识别结果以表格形式呈现
  - 支持导出为 Excel/CSV 格式
  - 实现:
    - `ocr_engine.py`: 添加 `recognize_table()` 方法，使用位置推断算法从 OCR 结果构建表格结构
    - `ocr_engine.py`: 添加 `export_table_to_csv()` 和 `export_table_to_excel()` 导出方法
    - `main_window.py`: 添加 `TableOCRWorker` 工作线程用于异步表格识别
    - `main_window.py`: 添加 `TableResultWidget` 组件显示表格结果（QTableWidget + HTML预览）
    - `main_window.py`: 添加表格模式切换按钮，支持文本/表格模式切换
    - `main_window.py`: 添加导出功能，支持 CSV 和 Excel 格式导出

- [x] Task 22: 添加文本编辑功能 (2026-01-31)
  - 允许用户在识别结果区域直接编辑文本
  - 添加撤销/重做功能
  - 编辑后的文本可以保存为文件
  - 实现:
    - `ResultTextWidget`: 添加编辑模式切换按钮，进入编辑模式时文本区可编辑
    - 添加撤销/重做按钮，调用 QTextEdit 内置 undo/redo 功能
    - 添加保存按钮，支持将编辑后的文本保存为 .txt 文件
    - 编辑模式下隐藏置信度控件，退出编辑模式后恢复置信度显示

- [x] Task 23: 优化启动速度 (2026-01-31)
  - 分析启动耗时，找出瓶颈: OCR 引擎在 `__init__` 中立即初始化，导入 paddle 和 paddleocr 耗时较长
  - 实现延迟加载 OCR 引擎（首次使用时初始化）:
    - 修改 `MainWindow.__init__`: 移除立即初始化，改为延迟加载
    - 新增 `setup_device_combo()`: 设置设备选择器而不初始化 OCR 引擎
    - 新增 `ensure_ocr_engine()`: 确保 OCR 引擎已初始化（懒加载）
    - 修改 `_process_pixmap()` 和 `process_image()`: 调用 `ensure_ocr_engine()` 确保引擎就绪
    - 修改 `_on_settings_changed()`: 清理引擎状态，下次使用时重新初始化
  - 添加启动画面显示加载进度:
    - 新增 `create_splash_screen()`: 创建美观的启动画面
    - 在 `main()` 中显示启动画面，主窗口加载完成后关闭
  - 目标: 启动时间 < 2 秒（界面立即显示，OCR 引擎后台延迟加载）

- [x] Task 24: 添加批量处理功能 (2026-01-31)
  - 支持选择多个图片文件批量识别
  - 显示批量处理进度
  - 结果可以导出为单个文本文件
  - 实现:
    - `BatchOCRWorker`: 后台批量处理工作线程，支持进度报告和停止功能
    - `BatchOCRDialog`: 批量处理对话框，包含文件列表、进度条、结果摘要
    - 工具栏添加"批量处理"按钮
    - 支持添加/移除/清空文件列表
    - 实时显示处理进度和当前文件
    - 处理完成后可导出所有结果为单个文本文件

### Phase 7: 高级功能和体验优化 (进行中)

- [x] Task 25: 添加数学公式识别功能 (2026-01-31)
  - 使用 PaddleOCR 的公式识别模型
  - 支持 LaTeX 格式输出
  - 在结果区域提供公式渲染预览
  - 实现:
    - `ocr_engine.py`: 添加 `recognize_formula()` 方法，支持 LaTeX 转换
    - `main_window.py`: 添加公式模式切换按钮和 FormulaResultWidget 组件
    - 添加 `FormulaOCRWorker` 异步处理工作线程
    - 支持复制 LaTeX 代码和纯文本结果
    - 添加 HTML 预览区域显示公式信息

- [x] Task 26: 实现智能段落合并 (2026-01-31)
  - 分析 OCR 结果的位置信息，自动合并属于同一段落的文本行
  - 支持多栏布局的识别结果整理
  - 提高长文本的可读性
  - 实现:
    - `ocr_engine.py`: 添加 `merge_paragraphs()` 方法，支持基于位置信息的段落合并
    - 添加 `_detect_columns()` 方法，使用直方图聚类算法检测多栏布局
    - 添加 `_merge_text_lines()` 方法，智能处理中英文文本合并
    - `main_window.py`:
      - 修改 `OCRWorker` 支持智能排版模式
      - 在 `ResultTextWidget` 添加"智能排版"开关按钮
      - 添加 `smartLayoutToggled` 信号和相关处理方法
      - 修改 `_on_ocr_finished()` 处理智能排版结果

- [x] Task 27: 添加识别结果翻译功能 (2026-01-31)
  - 集成翻译 API（支持离线词典）
  - 支持中英互译
  - 在结果区域显示原文和译文对照
  - 实现:
    - `translator.py`: 创建翻译模块（支持离线词典，包含 1000+ 常用词汇）
    - `main_window.py`: 添加翻译按钮和语言选择
    - 支持复制译文
    - 原文/译文对照显示，紫色主题区分
    - 自动语言检测（中文/英文/混合）
    - 翻译模式切换时自动刷新翻译结果

- [x] Task 28: 优化截图体验 (2026-01-31)
  - 添加截图时放大镜功能（显示光标附近的放大图像）
  - 支持截图时显示当前光标坐标
  - 添加截图区域的像素级调整（方向键微调）
  - 实现:
    - `screenshot_overlay.py`: 添加 `_draw_magnifier()` 方法，显示 120x120 像素的 2 倍放大视图
    - 添加 `coord_label` 坐标标签，实时显示光标位置
    - 添加 `_fine_tune_selection()` 方法，支持方向键微调选区（1 像素/次，Shift+方向键 10 像素/次）
    - 提示文字更新为"拖拽选择区域，按 Esc 取消 | 方向键微调选区"

- [x] Task 29: 添加快捷键自定义功能 (2026-01-31)

- [x] Task 31: [CRITICAL] 修复 pythonw.exe 运行时 OCR 初始化崩溃 (2026-01-31)

- [x] Task 32: [重要] 移除不应用逻辑代码实现的功能 (2026-01-31)
  - **原则**: 如果功能需要处理大量细节和边界情况，应交给 AI 模型，而非逻辑代码
  - **需要移除的功能**:
    1. **表格模式** (`TableResultWidget`, `TableOCRWorker`, `recognize_table`) - 边界情况太多
    2. **公式模式** (`FormulaResultWidget`, `FormulaOCRWorker`, `recognize_formula`) - 规则复杂
    3. **智能排版** (`merge_paragraphs`, `_detect_columns`, 智能排版按钮) - 需要语义理解
    4. **翻译功能** (`translator.py`, 翻译按钮, 翻译相关UI) - 需要语言理解
  - **保留的核心功能**:
    - 截图功能
    - 基本 OCR 文字识别
    - 复制到剪贴板
    - 历史记录
    - 设备选择 (CPU/GPU)
    - 快捷键
    - 系统托盘
  - **简化步骤**:
    1. `main_window.py`: 移除表格/公式模式按钮和相关 Worker
    2. `main_window.py`: 移除智能排版按钮和翻译按钮
    3. `main_window.py`: 移除 `TableResultWidget`, `FormulaResultWidget`
    4. `ocr_engine.py`: 移除 `recognize_table`, `recognize_formula`, `merge_paragraphs` 等方法
    5. 删除 `translator.py` 文件
    6. 简化 `ResultTextWidget`，移除翻译相关代码
  - **目标**: 代码量减少 50%+，专注于核心 OCR 功能
  - **验证**: 程序正常启动，截图识别功能正常
  - **修复后必须同步**: `cp -r src/* portable/src/`
  - **问题描述**: 使用 `portable/ScreenOCR.bat` 运行时，截图后弹出错误 "Failed to initialize OCR engine: 'NoneType' object has no attribute 'write'"
  - **根因**:
    1. `ScreenOCR.bat` 使用 `pythonw.exe` 运行（无控制台窗口）
    2. `pythonw.exe` 运行时 `sys.stdout` 和 `sys.stderr` 都是 `None`
    3. PaddleOCR/Paddle 初始化时尝试写入日志到 stdout，导致 `None.write()` 错误
  - **修复方案**: 在 `src/main.py` 程序入口处检测并重定向空的 stdout/stderr
    ```python
    import sys
    import os

    # 修复 pythonw.exe 运行时 stdout/stderr 为 None 的问题
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    ```
  - **验证方法**:
    1. 双击 `portable/ScreenOCR.bat` 启动
    2. 按 Ctrl+Shift+O 截图
    3. 应正常进行 OCR 识别，不再弹出错误
  - **涉及文件**: `src/main.py` (在最开头添加代码)
  - **修复后必须同步**: `cp -r src/* portable/src/`

- [x] Task 30: [CRITICAL] 修复截图功能严重问题 (2026-01-31)
  - **问题描述**:
    1. 按 ESC 无法退出截图模式
    2. 需要截多次图才能退出截图模式（不确定要截几次）
    3. 每截一个图片就弹出一个新窗口
  - **根因分析**:
    1. `main_window.py:2443-2446` 每次调用 `start_screenshot()` 时检查 `hasattr(self, '_screenshot_overlay')`，但 overlay 的 `captured` 信号被重复连接，导致每次截图触发多次 `_on_screenshot_captured`
    2. `screenshot_overlay.py` 的 `keyPressEvent` 可能没有正确获取键盘焦点
    3. overlay 隐藏后状态没有完全重置，导致需要多次截图
  - **修复要求**:
    1. 确保 overlay 只创建一次，信号只连接一次
    2. 在 `start()` 方法中强制获取键盘焦点: `self.grabKeyboard()`
    3. 在 `hideEvent()` 中释放键盘: `self.releaseKeyboard()`
    4. 确保每次截图完成后状态完全重置
    5. 添加右键点击取消截图功能作为 ESC 的备选
  - **验证方法**:
    1. 启动程序，按 Ctrl+Shift+O 开始截图
    2. 按 ESC 应该立即退出截图模式
    3. 截图一次后应该只弹出一个窗口，不是多个
    4. 重复测试 5 次确保稳定
  - **涉及文件**:
    - `src/screenshot_overlay.py` - 添加 grabKeyboard/releaseKeyboard
    - `src/main_window.py` - 修复信号重复连接问题
  - **修复后必须同步**: `cp -r src/* portable/src/`

## 运行方式

**用户运行**:
```
双击 portable/ScreenOCR.bat
```

**开发调试**:
```bash
D:/Anaconda3/envs/PaddleOCR/python.exe D:/5118/Archie/projects/paddleocr/src/main.py
```

**同步代码到 portable**:
```bash
cp -r D:/5118/Archie/projects/paddleocr/src/* D:/5118/Archie/projects/paddleocr/portable/src/
```
```

## 用户使用方式
1. 下载 `ScreenOCR.exe` (单个文件)
2. 双击运行
3. 按 `Ctrl+Shift+O` 截图识别
4. 结果自动复制到剪贴板

## 运行命令
```bash
mamba activate PaddleOCR
cd D:\5118\Archie\projects\paddleocr
python src/main.py
```

## 打包命令
```bash
mamba activate PaddleOCR
pyinstaller --onefile --windowed --icon=src/resources/icon.ico src/main.py -n ScreenOCR
```

## 验收标准
1. 用户可以通过快捷键一键截图识别
2. 识别结果准确，支持中英文混合
3. 界面美观，操作流畅
4. 可打包为独立 exe 分发给用户
5. 启动速度 < 3秒，识别速度 < 2秒

## 参考资料
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- PyQt6: https://www.riverbankcomputing.com/software/pyqt/
- mss: https://python-mss.readthedocs.io/
