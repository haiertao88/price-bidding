import streamlit as st
import pandas as pd
import io
import random
import string
import uuid
import base64
from datetime import datetime, timedelta
import hashlib
import json
import os
import time

# --- 页面配置、样式、数据持久化函数 保持不变 ---
# （此处省略原有不变的代码，仅粘贴修改/新增部分）

def render_admin_dashboard():
    """管理员端页面（新增产品信息+发布按钮）"""
    st.title("👑 华脉招采平台管理后台")
    st.divider()
    
    # 侧边栏菜单
    menu_option = st.sidebar.radio(
        "功能菜单",
        ["项目管理", "供应商库", "报价监控"],
        index=0,
        format_func=lambda x: f"📁 {x}" if x == "项目管理" else f"📇 {x}" if x == "供应商库" else f"📊 {x}"
    )
    
    # 1. 项目管理（核心改造：新增产品信息+发布按钮）
    if menu_option == "项目管理":
        st.markdown("### 📁 项目管理")
        
        # 新建项目（新增产品信息字段）
        with st.expander("➕ 新建项目", expanded=True):
            with st.form("create_project_form", border=True):
                # 原有项目基本信息
                col1, col2 = st.columns(2)
                with col1:
                    project_name = st.text_input("项目名称 *", placeholder="请输入项目全称")
                    project_deadline_date = st.date_input("截止日期 *", value=datetime.now() + timedelta(days=7))
                with col2:
                    project_deadline_time = st.time_input("截止时间 *", value=datetime.strptime("17:00", "%H:%M").time())
                    available_suppliers = list(global_data["suppliers"].keys())
                    selected_suppliers = st.multiselect(
                        "参与供应商 *",
                        options=available_suppliers,
                        placeholder="请选择至少一个供应商",
                        disabled=not available_suppliers
                    )
                
                # 新增：产品信息字段
                st.markdown("#### 📦 产品信息")
                col3, col4, col5 = st.columns(3)
                with col3:
                    product_name = st.text_input("产品名称 *", placeholder="如：分纤箱、光纤光缆")
                with col4:
                    product_quantity = st.number_input("产品数量 *", min_value=1, step=1, value=1, help="必填，最小为1")
                with col5:
                    product_unit = st.text_input("产品单位 *", placeholder="如：个、米、套", value="个")
                
                # 产品要求（多行文本）
                product_requirements = st.text_area(
                    "产品要求 *", 
                    placeholder="请输入详细的产品规格、技术参数、交付要求等",
                    height=100
                )
                
                create_btn = st.form_submit_button("🚀 创建项目", type="primary")
                if create_btn:
                    with st.spinner("正在创建项目..."):
                        time.sleep(1)
                        # 校验新增字段
                        if not project_name:
                            st.error("项目名称不能为空！")
                        elif not available_suppliers:
                            st.error("请先在【供应商库】添加供应商！")
                        elif not selected_suppliers:
                            st.error("请至少选择一个参与供应商！")
                        elif not product_name:
                            st.error("产品名称不能为空！")
                        elif not product_unit:
                            st.error("产品单位不能为空！")
                        elif not product_requirements:
                            st.error("产品要求不能为空！")
                        else:
                            # 生成项目数据（包含产品信息）
                            project_id = str(uuid.uuid4())[:8]
                            deadline_str = f"{project_deadline_date} {project_deadline_time.strftime('%H:%M')}"
                            supplier_codes = {sup: generate_random_code() for sup in selected_suppliers}
                            
                            # 添加到全局数据（新增产品信息）
                            global_data["projects"][project_id] = {
                                "name": project_name,
                                "deadline": deadline_str,
                                "codes": supplier_codes,
                                "products": {  # 产品信息
                                    "name": product_name,
                                    "quantity": product_quantity,
                                    "unit": product_unit,
                                    "requirements": product_requirements
                                },
                                "quotes": {},
                                "is_published": False  # 新增：是否发布给供应商
                            }
                            
                            # 持久化保存
                            if save_data(global_data):
                                st.markdown("""
                                    <div class="success-box">
                                        <strong>项目创建成功</strong>！
                                        <br>项目ID：{}
                                        <br>请点击「发布给供应商」按钮，将项目推送给选中的供应商。
                                    </div>
                                """.format(project_id), unsafe_allow_html=True)
                            else:
                                st.error("项目创建失败，请重试！")
        
        # 现有项目列表（核心改造：展示产品信息+发布按钮）
        st.markdown("### 📋 现有项目")
        projects = global_data.get("projects", {})
        if not projects:
            st.info("暂无项目数据，点击上方「新建项目」创建第一个项目！")
        else:
            sorted_projects = sorted(
                projects.items(),
                key=lambda x: safe_parse_deadline(x[1]["deadline"]),
                reverse=False
            )
            
            for project_id, project_data in sorted_projects:
                # 提取产品信息
                product_info = project_data.get("products", {})
                product_name = product_info.get("name", "未填写")
                product_quantity = product_info.get("quantity", 0)
                product_unit = product_info.get("unit", "未填写")
                product_requirements = product_info.get("requirements", "未填写")
                is_published = project_data.get("is_published", False)
                total_suppliers = len(project_data["codes"])
                submitted_quotes = len(project_data.get("quotes", {}))
                
                with st.expander(f"📅 {project_data['name']}（截止：{project_data['deadline']}）", expanded=False):
                    # 项目信息卡片（新增产品信息）
                    st.markdown(f"""
                        <div class="card">
                            <div><strong>项目ID：</strong>{project_id}</div>
                            <div><strong>参与供应商：</strong>{', '.join(project_data['codes'].keys())}</div>
                            <div><strong>已提交报价：</strong>{submitted_quotes}/{total_suppliers}</div>
                            <hr style="margin: 0.5rem 0;">
                            <div><strong>产品名称：</strong>{product_name}</div>
                            <div><strong>产品数量：</strong>{product_quantity} {product_unit}</div>
                            <div><strong>产品要求：</strong>{product_requirements}</div>
                            <hr style="margin: 0.5rem 0;">
                            <div><strong>发布状态：</strong>{"✅ 已发布" if is_published else "❌ 未发布"}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # 操作按钮：发布、编辑、删除
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        # 发布给供应商按钮（核心新增）
                        publish_btn = st.button(
                            "📤 发布给供应商" if not is_published else "🔄 重新发布",
                            key=f"publish_{project_id}",
                            type="primary" if not is_published else "secondary"
                        )
                        if publish_btn:
                            with st.spinner("正在发布项目给供应商..."):
                                time.sleep(1)
                                # 更新发布状态
                                global_data["projects"][project_id]["is_published"] = True
                                # 持久化保存
                                if save_data(global_data):
                                    st.markdown("""
                                        <div class="success-box">
                                            <strong>发布成功</strong>！供应商可登录系统查看该项目并提交报价。
                                        </div>
                                    """, unsafe_allow_html=True)
                                    # 刷新页面
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("发布失败，请重试！")
                    
                    with col2:
                        # 编辑按钮（预留：可扩展编辑产品信息）
                        edit_btn = st.button("✏️ 编辑", key=f"edit_{project_id}", type="secondary")
                        if edit_btn:
                            st.warning("编辑功能暂未实现，如需修改请删除项目后重新创建！")
                    
                    with col3:
                        # 删除按钮
                        del_btn = st.button("🗑️ 删除", key=f"del_{project_id}", type="secondary")
                        if del_btn:
                            with st.spinner("正在删除项目..."):
                                time.sleep(0.5)
                                del global_data["projects"][project_id]
                                if save_data(global_data):
                                    st.success("项目删除成功！")
                                    st.rerun()
                                else:
                                    st.error("项目删除失败，请重试！")
    
    # 供应商库、报价监控模块 保持不变
    # ...（此处省略原有不变的代码）

# --- 其余函数（render_login_page、render_supplier_dashboard等）保持不变 ---
# --- 主程序入口保持不变 ---
