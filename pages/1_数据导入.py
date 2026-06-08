import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    generate_all_data,
    save_session_data,
    parse_uploaded_file,
    validate_data,
    export_to_excel,
    PRODUCTION_LINES,
    TEAMS,
    SHIFTS,
)

st.set_page_config(
    page_title="数据导入 - 能耗分析看板",
    page_icon="📤",
    layout="wide",
)

with st.sidebar:
    st.title("⚡ 能耗分析看板")
    st.markdown("---")
    st.page_link("app.py", label="📊 总览页", icon="📊")
    st.page_link("pages/1_数据导入.py", label="📤 数据导入", icon="📤")
    st.page_link("pages/2_产线分析.py", label="🏭 产线分析", icon="🏭")
    st.page_link("pages/3_班组对比.py", label="👥 班组对比", icon="👥")
    st.page_link("pages/4_异常清单.py", label="⚠️ 异常清单", icon="⚠️")

st.title("📤 数据导入")
st.markdown("---")

st.markdown("### 🎯 快速开始 - 生成模拟数据")
st.info("点击下方按钮可直接生成模拟数据，包含电表、产量、班组和设备状态数据，用于演示和测试。")

col1, col2, col3 = st.columns(3)

with col1:
    days = st.slider("数据天数", min_value=7, max_value=90, value=30, step=7)

with col2:
    freq = st.selectbox("采样频率", options=["15min", "30min", "1H"], index=0)

with col3:
    st.markdown("")
    generate_btn = st.button("🔄 生成模拟数据", type="primary", use_container_width=True)

if generate_btn:
    with st.spinner("正在生成模拟数据..."):
        data = generate_all_data(days=days, freq=freq)
        save_session_data(st, data)
        st.success(f"✅ 成功生成 {days} 天的模拟数据！")

st.markdown("---")
st.markdown("### 📁 上传数据文件")
st.info("支持上传 CSV 或 Excel 文件。请确保包含必需的列：电表数据需包含 timestamp、production_line、power_kw、is_running；产量数据需包含 date、production_line、power_consumption_kwh、output_quantity。")

uploaded_files = st.file_uploader(
    "选择数据文件（可多选）",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True,
    help="电表数据文件名建议包含 'meter'，产量数据包含 'production'，班组数据包含 'schedule'，设备数据包含 'equipment'",
)

if uploaded_files:
    data_dict = {}
    for uploaded_file in uploaded_files:
        filename = uploaded_file.name.lower()
        df = parse_uploaded_file(uploaded_file)
        if df is not None:
            if "meter" in filename:
                data_dict["meter"] = df
            elif "production" in filename:
                data_dict["production"] = df
            elif "schedule" in filename or "team" in filename:
                data_dict["schedule"] = df
            elif "equipment" in filename or "status" in filename:
                data_dict["equipment"] = df
            else:
                st.warning(f"⚠️ 无法自动识别文件类型: {uploaded_file.name}")

    if data_dict:
        validation = validate_data(data_dict)
        if validation["is_valid"]:
            if st.button("💾 保存上传数据", type="primary"):
                if "data" in st.session_state and st.session_state["data"]:
                    st.session_state["data"].update(data_dict)
                else:
                    st.session_state["data"] = data_dict
                st.success("✅ 数据保存成功！")
        else:
            st.error("❌ 数据验证失败：")
            for issue in validation["issues"]:
                st.markdown(f"- {issue}")

st.markdown("---")
st.markdown("### 📋 当前数据状态")

if "data" in st.session_state and st.session_state["data"]:
    data = st.session_state["data"]

    tab1, tab2, tab3, tab4 = st.tabs(["📊 电表数据", "📦 产量数据", "📅 班组排班", "⚙️ 设备状态"])

    with tab1:
        if "meter" in data and not data["meter"].empty:
            df = data["meter"]
            st.markdown(f"**数据行数:** {len(df):,}")
            st.markdown(f"**时间范围:** {df['timestamp'].min()} ~ {df['timestamp'].max()}")
            st.markdown(f"**产线数量:** {df['production_line'].nunique()}")
            st.dataframe(df.head(100), use_container_width=True, height=300)
        else:
            st.warning("暂无电表数据")

    with tab2:
        if "production" in data and not data["production"].empty:
            df = data["production"]
            st.markdown(f"**数据行数:** {len(df):,}")
            st.markdown(f"**日期范围:** {df['date'].min()} ~ {df['date'].max()}")
            st.markdown(f"**总耗电量:** {df['power_consumption_kwh'].sum():,.2f} kWh")
            st.markdown(f"**总产量:** {df['output_quantity'].sum():,.2f}")
            st.dataframe(df.head(100), use_container_width=True, height=300)
        else:
            st.warning("暂无产量数据")

    with tab3:
        if "schedule" in data and not data["schedule"].empty:
            df = data["schedule"]
            st.markdown(f"**数据行数:** {len(df):,}")
            st.markdown(f"**日期范围:** {df['date'].min()} ~ {df['date'].max()}")
            st.dataframe(df.head(100), use_container_width=True, height=300)
        else:
            st.warning("暂无班组排班数据")

    with tab4:
        if "equipment" in data and not data["equipment"].empty:
            df = data["equipment"]
            st.markdown(f"**状态变化次数:** {len(df):,}")
            st.dataframe(df.head(100), use_container_width=True, height=300)
        else:
            st.warning("暂无设备状态数据")

    st.markdown("---")
    st.markdown("### 💾 导出数据")
    st.info("可将当前所有数据导出为 Excel 文件，方便备份或离线分析。")

    export_data = {}
    for key, df in data.items():
        if df is not None and not df.empty:
            export_df = df.copy()
            if "timestamp" in export_df.columns:
                export_df["timestamp"] = export_df["timestamp"].astype(str)
            if "date" in export_df.columns:
                export_df["date"] = export_df["date"].astype(str)
            export_data[key] = export_df

    if export_data:
        excel_data = export_to_excel(export_data)
        st.download_button(
            label="📥 下载全部数据 (Excel)",
            data=excel_data,
            file_name=f"能耗数据_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    if st.button("🗑️ 清空所有数据", use_container_width=True):
        st.session_state["data"] = None
        st.success("✅ 数据已清空")
        st.rerun()

else:
    st.info("💡 请先点击上方【生成模拟数据】按钮或上传数据文件")

st.markdown("---")
st.markdown("### 📖 数据说明")

with st.expander("📚 查看数据字段说明"):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**电表数据字段:**")
        st.markdown("- `timestamp`: 采样时间戳")
        st.markdown("- `production_line`: 产线名称")
        st.markdown("- `team`: 当班班组")
        st.markdown("- `shift`: 班次（早/中/晚）")
        st.markdown("- `power_kw`: 瞬时功率 (kW)")
        st.markdown("- `is_running`: 设备是否运行 (1=运行, 0=停机)")
        st.markdown("- `hour`: 小时")
        st.markdown("- `is_peak`: 是否峰段")
        st.markdown("- `is_valley`: 是否谷段")
        st.markdown("- `is_flat`: 是否平段")

    with col2:
        st.markdown("**产量数据字段:**")
        st.markdown("- `date`: 日期")
        st.markdown("- `production_line`: 产线名称")
        st.markdown("- `team`: 班组")
        st.markdown("- `shift`: 班次")
        st.markdown("- `running_hours`: 运行时长 (小时)")
        st.markdown("- `power_consumption_kwh`: 耗电量 (kWh)")
        st.markdown("- `output_quantity`: 产量")
        st.markdown("- `unit_energy_consumption`: 单位产量能耗")

    st.markdown("---")
    st.markdown("**模拟数据配置:**")
    st.markdown(f"- **产线:** {', '.join(PRODUCTION_LINES)}")
    st.markdown(f"- **班组:** {', '.join(TEAMS)}")
    st.markdown(f"- **班次:** {', '.join(SHIFTS)}")
    st.markdown("- **峰段:** 08:00-12:00, 17:00-21:00")
    st.markdown("- **谷段:** 00:00-06:00")
    st.markdown("- **平段:** 其余时段")
