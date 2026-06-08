import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
from utils import set_plotly_chinese_font

print("=== 测试1: make_subplots 子图标题 ===")
fig = make_subplots(rows=2, cols=1, subplot_titles=('日用电量趋势', '空载电耗占比'))
fig.add_trace(go.Scatter(x=[1,2,3], y=[10,20,30], name='测试'), row=1, col=1)
print(f'修复前 annotations 数量: {len(fig.layout.annotations)}')
print(f'修复前子图标题1: {fig.layout.annotations[0].text}')
print(f'修复前子图标题2: {fig.layout.annotations[1].text}')

fig = set_plotly_chinese_font(fig)
print(f'修复后 annotations 数量: {len(fig.layout.annotations)}')
print(f'修复后子图标题1: {fig.layout.annotations[0].text}')
print(f'修复后子图标题2: {fig.layout.annotations[1].text}')
print(f'修复后子图标题1字体: {fig.layout.annotations[0].font.family}')
print(f'修复后子图标题2字体: {fig.layout.annotations[1].font.family}')

print("\n=== 测试2: 异常类型分布图（水平条形图） ===")
df = pd.DataFrame({
    '异常类型': ['停机高耗电', '低产高耗电', '电耗波动', '数据缺失'],
    '次数': [15, 23, 8, 5]
})
fig2 = px.bar(df, y='异常类型', x='次数', title='异常类型分布', orientation='h')
title_font = fig2.layout.title.font.family if fig2.layout.title.font else "默认"
print(f'修复前标题字体: {title_font}')
fig2 = set_plotly_chinese_font(fig2)
print(f'修复后标题字体: {fig2.layout.title.font.family}')
print(f'修复后x轴标题字体: {fig2.layout.xaxis.title.font.family}')
print(f'修复后y轴标题字体: {fig2.layout.yaxis.title.font.family}')

print("\n=== 测试3: 多子图多坐标轴 ===")
fig3 = make_subplots(rows=2, cols=2, 
                     subplot_titles=('图表1', '图表2', '图表3', '图表4'))
fig3.add_trace(go.Bar(x=['A','B','C'], y=[1,2,3]), row=1, col=1)
fig3.add_trace(go.Scatter(x=[1,2,3], y=[3,1,2]), row=1, col=2)
fig3.add_trace(go.Pie(labels=['X','Y','Z'], values=[30,50,20]), row=2, col=1)
fig3.add_trace(go.Box(y=[1,2,3,4,5]), row=2, col=2)
print(f'修复前 annotations 数量: {len(fig3.layout.annotations)}')
fig3 = set_plotly_chinese_font(fig3)
print(f'修复后 annotations 数量: {len(fig3.layout.annotations)}')
for i, ann in enumerate(fig3.layout.annotations):
    print(f'  子图标题{i+1}: {ann.text} (字体: {ann.font.family})')

# 检查所有坐标轴
print(f"\n坐标轴检查:")
for i in range(1, 5):
    xaxis_key = f'xaxis{i}' if i > 1 else 'xaxis'
    yaxis_key = f'yaxis{i}' if i > 1 else 'yaxis'
    xaxis = fig3.layout.get(xaxis_key)
    yaxis = fig3.layout.get(yaxis_key)
    if xaxis:
        print(f'  {xaxis_key} 标题字体: {xaxis.title.font.family if xaxis.title else "无标题"}')
    if yaxis:
        print(f'  {yaxis_key} 标题字体: {yaxis.title.font.family if yaxis.title else "无标题"}')

print("\n✅ 所有测试通过！")
