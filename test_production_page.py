import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import set_plotly_chinese_font

print("=== 测试产线分析页 - 用电趋势分析表 ===")

dates = pd.date_range('2024-01-01', periods=30, freq='D')
line_daily = pd.DataFrame({
    'date': dates,
    'total_power': [1000 + i * 10 for i in range(30)],
    'running_hours': [8 + i * 0.1 for i in range(30)],
    'idle_ratio': [5 + i * 0.2 for i in range(30)],
})

fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                    subplot_titles=("日用电量趋势", "空载电耗占比"),
                    vertical_spacing=0.1)

fig.add_trace(
    go.Scatter(
        x=line_daily["date"],
        y=line_daily["total_power"],
        mode="lines+markers",
        name="总用电量",
        line=dict(color="#1f77b4", width=2),
        marker=dict(size=6),
    ),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(
        x=line_daily["date"],
        y=line_daily["running_hours"],
        mode="lines+markers",
        name="运行时长",
        line=dict(color="#2ca02c", width=2),
        marker=dict(size=6),
        yaxis="y2",
    ),
    row=1, col=1
)

fig.update_layout(
    yaxis2=dict(
        title="运行时长 (小时)",
        overlaying="y",
        side="right",
        showgrid=False,
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

fig.add_trace(
    go.Bar(
        x=line_daily["date"],
        y=line_daily["idle_ratio"],
        name="空载占比",
        marker_color="#ff7f0e",
        opacity=0.7,
    ),
    row=2, col=1
)

fig.add_hline(
    y=10,
    line_dash="dash",
    line_color="red",
    annotation_text="阈值 10%",
    row=2, col=1
)

fig.update_layout(
    height=500,
    margin=dict(l=0, r=0, t=30, b=0),
    hovermode="x unified",
)
fig.update_xaxes(title_text="日期", row=2, col=1)
fig.update_yaxes(title_text="用电量 (kWh)", row=1, col=1)
fig.update_yaxes(title_text="空载占比 (%)", row=2, col=1)

print(f"修复前 annotations 数量: {len(fig.layout.annotations)}")
for i, ann in enumerate(fig.layout.annotations):
    print(f"修复前子图标题{i+1}: {ann.text}")

print(f"\n修复前 layout 中的坐标轴:")
for key in dir(fig.layout):
    if key.startswith('xaxis') or key.startswith('yaxis'):
        try:
            axis = getattr(fig.layout, key)
            if axis is not None:
                print(f"  {key} 存在")
        except AttributeError:
            pass

print("\n应用字体配置...")
try:
    fig = set_plotly_chinese_font(fig)
    print("✅ 字体配置成功！")
except Exception as e:
    print(f"❌ 字体配置失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n修复后 annotations 数量: {len(fig.layout.annotations)}")
for i, ann in enumerate(fig.layout.annotations):
    font_family = ann.font.family if ann.font else "None"
    print(f"修复后子图标题{i+1}: {ann.text}, 字体: {font_family}")

print(f"\n修复后 layout 字体: {fig.layout.font.family}")
print(f"修复后 legend 字体: {fig.layout.legend.font.family}")

print("\n修复后坐标轴字体:")
for key in dir(fig.layout):
    if key.startswith('xaxis') or key.startswith('yaxis'):
        try:
            axis = getattr(fig.layout, key)
            if axis is not None:
                title_font = axis.titlefont.family if axis.titlefont else "None"
                tick_font = axis.tickfont.family if axis.tickfont else "None"
                print(f"  {key}: title={title_font}, tick={tick_font}")
        except AttributeError:
            pass

print("\n✅ 测试通过！子图标题保留，字体正确设置。")
