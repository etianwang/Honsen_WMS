# Inventory_page.py
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QMessageBox, QApplication, QLabel, QDialog, QFileDialog,
    QComboBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
import os
import db_manager
from add_item_dialog import AddItemDialog
from edit_item_dialog import EditItemDialog
from batch_edit_dialog import BatchEditDialog
from theme.loader import apply_widget_role

class InventoryPage(QWidget):
    """
    库存管理界面：展示和操作 Inventory 表数据。
    实现：根据库存状态（缺货/预警）设置行背景色。
    新增：支持多选和批量编辑功能，以及刷新按钮。
    扩展：增加类别、专业、储存位置筛选功能。
    【更新】表格仅保留“柜号”列 (已合并初始柜号)。
    """
    def __init__(self, db_path: str):
        super().__init__()
        self.setObjectName("contentPage")
        self.db_path = db_path
        self.all_data = []  # 存储所有数据用于筛选
        self.init_ui()
        self.load_Inventory_data()

    def init_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(16, 16, 16, 16)
        page_layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("pageCard")
        main_layout = QVBoxLayout(card)
        main_layout.setContentsMargins(16, 16, 16, 12)
        main_layout.setSpacing(12)

        # --- 1. 顶部操作栏 (工具栏) ---
        toolbar_layout = QHBoxLayout()
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索：名称、型号 或 柜号...")
        self.search_input.textChanged.connect(self.filter_data)
        toolbar_layout.addWidget(self.search_input)
        
        # 类别筛选
        toolbar_layout.addWidget(QLabel("类别:"))
        self.category_filter_combo = QComboBox()
        self.category_filter_combo.setFixedWidth(120)
        self.category_filter_combo.addItem("ALL")
        self.category_filter_combo.currentTextChanged.connect(self.filter_data)
        toolbar_layout.addWidget(self.category_filter_combo)
        
        # 专业筛选
        toolbar_layout.addWidget(QLabel("专业:"))
        self.domain_filter_combo = QComboBox()
        self.domain_filter_combo.setFixedWidth(120)
        self.domain_filter_combo.addItem("ALL")
        self.domain_filter_combo.currentTextChanged.connect(self.filter_data)
        toolbar_layout.addWidget(self.domain_filter_combo)
        
        # 储存位置筛选
        toolbar_layout.addWidget(QLabel("储存位置:"))
        self.location_filter_combo = QComboBox()
        self.location_filter_combo.setFixedWidth(120)
        self.location_filter_combo.addItem("ALL")
        self.location_filter_combo.currentTextChanged.connect(self.filter_data)
        toolbar_layout.addWidget(self.location_filter_combo)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        apply_widget_role(self.refresh_btn, "warning")
        self.refresh_btn.setToolTip("从数据库重新加载最新数据")
        self.refresh_btn.clicked.connect(self.refresh_data)
        toolbar_layout.addWidget(self.refresh_btn)
        
        toolbar_layout.addStretch(1)
        
        # 按钮
        self.add_btn = QPushButton("新增物品")
        self.edit_btn = QPushButton("编辑物品")
        self.batch_edit_btn = QPushButton("批量编辑")
        self.del_btn = QPushButton("删除物品")

        apply_widget_role(self.add_btn, "success")
        apply_widget_role(self.edit_btn, "info")
        apply_widget_role(self.batch_edit_btn, "accent")
        apply_widget_role(self.del_btn, "danger")
        
        # 连接信号
        self.add_btn.clicked.connect(self.add_item_dialog)
        self.edit_btn.clicked.connect(self.edit_item_dialog) 
        self.batch_edit_btn.clicked.connect(self.batch_edit_action)
        self.del_btn.clicked.connect(self.delete_item_action) 

        toolbar_layout.addWidget(self.add_btn)
        toolbar_layout.addWidget(self.edit_btn)
        toolbar_layout.addWidget(self.batch_edit_btn)
        toolbar_layout.addWidget(self.del_btn)
        
        main_layout.addLayout(toolbar_layout)

        # --- 2. 主数据表格 ---
        self.Inventory_table = QTableWidget()
        self.Inventory_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.Inventory_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.Inventory_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.Inventory_table.setAlternatingRowColors(True)

        # 定义表头：【修改】移除"初始柜号"，只保留"柜号"
        # 索引: 0:ID, 1:Name, 2:Ref, 3:Category, 4:Domain, 5:Unit, 
        #      6:Current, 7:Min, 8:Location, 9:Cabinet, 10:Status
        self.headers = [
            "ID", "名称 (Name)", "物品型号 (Ref)", "材料类别", "专业类别", "单位 (Unit)", 
            "当前库存", "最小库存", "储存位置", "柜号", "库存状态"
        ]
        self.Inventory_table.setColumnCount(len(self.headers))
        self.Inventory_table.setHorizontalHeaderLabels(self.headers)
        
        # 调整列宽
        # self.Inventory_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # self.Inventory_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header = self.Inventory_table.horizontalHeader()
        main_layout.addWidget(self.Inventory_table)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        self.Inventory_table.setColumnWidth(1, 300) 
        self.Inventory_table.setColumnWidth(5, 70)
        self.Inventory_table.setColumnWidth(4, 60) 
        self.Inventory_table.setColumnWidth(3, 80) 
        self.Inventory_table.setColumnWidth(2, 200)
        self.Inventory_table.setColumnWidth(6, 60)
        self.Inventory_table.setColumnWidth(7, 60)
        self.Inventory_table.setColumnWidth(8, 60)
        self.Inventory_table.setColumnWidth(9, 100)
        self.Inventory_table.setColumnWidth(10, 60)
        # 底部状态栏
        self.status_label = QLabel("总计 0 条记录。")
        self.status_label.setObjectName("pageStatusBar")
        main_layout.addWidget(self.status_label)
        
        # 连接选择变化信号
        self.Inventory_table.itemSelectionChanged.connect(self.update_status_label)

        page_layout.addWidget(card)


    def load_Inventory_data(self):
        """从数据库加载数据并填充表格"""
        print("⏳ [Load] 开始从数据库读取...")
        data = db_manager.get_all_Inventory(self.db_path)
        print(f"✅ [Load] 读取完成，共 {len(data)} 条数据。开始填充表格...")
        # 保存所有数据用于筛选
        self.all_data = data
        
        # 刷新筛选下拉框选项
        self._refresh_filter_dropdowns()
        
        # 填充表格
        self._populate_table(data)
        
        # 应用当前筛选
        self.filter_data()
    


    def _refresh_filter_dropdowns(self):
        """刷新筛选下拉框的选项"""
        if not self.all_data:
            return
        
        # 保存当前选择
        current_category = self.category_filter_combo.currentText()
        current_domain = self.domain_filter_combo.currentText()
        current_location = self.location_filter_combo.currentText()
        
        # 提取所有唯一的类别
        categories = set()
        for item in self.all_data:
            category = item.get('category', '').strip()
            if category:
                categories.add(category)
        
        # 提取所有唯一的专业
        domains = set()
        for item in self.all_data:
            domain = item.get('domain', '').strip()
            if domain:
                domains.add(domain)
        
        # 提取所有唯一的储存位置
        locations = set()
        for item in self.all_data:
            location = item.get('location', '').strip()
            if location:
                locations.add(location)
        
        # 更新类别下拉框
        self.category_filter_combo.blockSignals(True)
        self.category_filter_combo.clear()
        self.category_filter_combo.addItem("ALL")
        self.category_filter_combo.addItems(sorted(list(categories)))
        cat_index = self.category_filter_combo.findText(current_category)
        if cat_index >= 0:
            self.category_filter_combo.setCurrentIndex(cat_index)
        self.category_filter_combo.blockSignals(False)
        
        # 更新专业下拉框
        self.domain_filter_combo.blockSignals(True)
        self.domain_filter_combo.clear()
        self.domain_filter_combo.addItem("ALL")
        self.domain_filter_combo.addItems(sorted(list(domains)))
        dom_index = self.domain_filter_combo.findText(current_domain)
        if dom_index >= 0:
            self.domain_filter_combo.setCurrentIndex(dom_index)
        self.domain_filter_combo.blockSignals(False)
        
        # 更新储存位置下拉框
        self.location_filter_combo.blockSignals(True)
        self.location_filter_combo.clear()
        self.location_filter_combo.addItem("ALL")
        self.location_filter_combo.addItems(sorted(list(locations)))
        loc_index = self.location_filter_combo.findText(current_location)
        if loc_index >= 0:
            self.location_filter_combo.setCurrentIndex(loc_index)
        self.location_filter_combo.blockSignals(False)

    def _populate_table(self, data):
        """填充表格数据 - 【增强版：自动为截断文本添加 ToolTip】"""
        print(f"⚙️ [Render] 准备渲染 {len(data)} 行数据...")
        
        # 🔥【关键优化 1】暂停界面重绘
        self.Inventory_table.setUpdatesEnabled(False)
        self.Inventory_table.setSortingEnabled(False)
        
        try:
            self.Inventory_table.setRowCount(len(data))
            
            # --- 🌟 数据聚合分析 (保持不变，用于生成高级 Tooltip) ---
            global_item_map = {} 
            name_model_map = {} 

            for item in data:
                name = str(item.get('name', '')).strip()
                ref = str(item.get('reference', '')).strip()
                loc = str(item.get('location', '')).strip() or "未指定位置"
                cab = str(item.get('cabinet', '')).strip() or "无柜号"
                
                try:
                    stock = int(item.get('current_stock', 0))
                except ValueError:
                    stock = 0
                
                if not name:
                    continue

                key = (name, ref)
                if key not in global_item_map:
                    global_item_map[key] = {'total': 0, 'locations': set(), 'cabinets': set(), 'unit': item.get('unit', '')}
                
                global_item_map[key]['total'] += stock
                global_item_map[key]['locations'].add(loc)
                global_item_map[key]['cabinets'].add(f"{loc}-{cab}")

                if name not in name_model_map:
                    name_model_map[name] = {}
                if ref not in name_model_map[name]:
                    name_model_map[name][ref] = 0
                name_model_map[name][ref] += stock
            # -------------------------------------------------------

            critical_color = QColor(255, 179, 179)
            warning_color = QColor(255, 240, 192)
            default_color = QColor(255, 255, 255)
            
            # 获取字体度量器，用于计算文本像素宽度
            font_metrics = self.Inventory_table.fontMetrics()

            for row_index, item in enumerate(data):
                # 1. 计算库存状态和颜色
                current = item['current_stock']
                minimum = item['min_stock']
                status_text = "正常"
                color = default_color
                
                if current <= 0:
                    status_text = "缺货"
                    color = critical_color
                elif current <= minimum:
                    status_text = "预警"
                    color = warning_color
                
                # 2. 构建智能显示名称 (用于表格显示)
                name = item['name']
                location = item.get('location', '')
                cabinet = item.get('cabinet', '')
                
                display_name = name
                if location:
                    display_name += f" 📍[{location}]"
                if cabinet:
                    display_name += f" 🗄️({cabinet})"
                
                # 3. 🌟 构建名称列的终极版 ToolTip (保持原有逻辑)
                ref = item.get('reference', '')
                unit = item.get('unit', '')
                key = (name, ref)
                
                current_global = global_item_map.get(key, {'total': 0, 'locations': set(), 'cabinets': set()})
                total_stock = current_global['total']
                all_locations = sorted(list(current_global['locations']))
                all_cabinets = sorted(list(current_global['cabinets']))
                
                other_models_stock = 0
                other_models_info = []
                if name in name_model_map:
                    for other_ref, stock_val in name_model_map[name].items():
                        if other_ref != ref:
                            other_models_stock += stock_val
                            other_models_info.append(f"{other_ref}: {stock_val}")
                
                tooltip_parts = []
                tooltip_parts.append(f"<div style='font-family: Arial; font-size: 13px;'>")
                tooltip_parts.append(f"<b style='font-size: 14px; color: #1976D2;'>📦 {name}</b>")
                tooltip_parts.append(f"<br><b>型号:</b> {ref} | <b>单位:</b> {unit}")
                tooltip_parts.append(f"<br><b>当前位置:</b> {location or '未指定'} - {cabinet or '无'}")
                tooltip_parts.append(f"<br><b>当前库存:</b> <span style='font-weight:bold; font-size:15px;'>{current}</span> {unit}")
                tooltip_parts.append("<hr style='border: 0; border-top: 1px solid #ddd; margin: 5px 0;'>")
                
                if len(all_locations) > 1 or (len(all_locations) == 1 and len(all_cabinets) > 1):
                    tooltip_parts.append(f"<b style='color: #D32F2F;'>🌍 全局总库存: {total_stock} {unit}</b>")
                    tooltip_parts.append(f"<br><i>(分布在 {len(all_locations)} 个位置，共 {len(all_cabinets)} 个存储点)</i>")
                    loc_text = ", ".join(all_locations[:5])
                    if len(all_locations) > 5: loc_text += f"... (+{len(all_locations)-5})"
                    tooltip_parts.append(f"<br><b>📍 涉及位置:</b> {loc_text}")
                    cab_text = ", ".join(all_cabinets[:5])
                    if len(all_cabinets) > 5: cab_text += f"... (+{len(all_cabinets)-5})"
                    tooltip_parts.append(f"<br><b>🗄️ 具体柜号:</b> {cab_text}")
                else:
                    tooltip_parts.append(f"<b style='color: #388E3C;'>✅ 全局总库存: {total_stock} {unit}</b> (唯一记录)")
                
                tooltip_parts.append("<hr style='border: 0; border-top: 1px solid #ddd; margin: 5px 0;'>")
                
                if other_models_stock > 0:
                    tooltip_parts.append(f"<b style='color: #F57C00;'>🔄 同名其他型号总库存: {other_models_stock} {unit}</b>")
                    tooltip_parts.append(f"<br><i>(共 {len(other_models_info)} 种其他型号)</i>")
                    models_preview = ", ".join(other_models_info[:5])
                    if len(other_models_info) > 5: models_preview += f"... (+{len(other_models_info)-5})"
                    tooltip_parts.append(f"<br><b>详情:</b> {models_preview}")
                else:
                    tooltip_parts.append(f"<i style='color: #999;'>暂无同名其他型号记录</i>")

                tooltip_parts.append("<hr style='border: 0; border-top: 1px solid #ddd; margin: 5px 0;'>")
                tooltip_parts.append(f"<b>类别:</b> {item.get('category', '其他')} | <b>专业:</b> {item.get('domain', '其他')}")
                tooltip_parts.append(f"<br><b>最小库存警戒线:</b> {minimum}")
                tooltip_parts.append("</div>")
                
                advanced_tooltip = "".join(tooltip_parts)

                # ================= 核心修改开始：通用 ToolTip 设置逻辑 =================
                
                # 定义需要处理的列索引和对应的数据源
                # 格式：(列索引, 显示文本变量, 是否使用高级Tooltip(仅名称列))
                columns_to_process = [
                    (1, display_name, True),   # 名称列 (使用高级 HTML Tooltip)
                    (2, ref, False),           # 型号
                    (3, item.get('category', '其他'), False), # 类别
                    (4, item.get('domain', '其他'), False),   # 专业
                    (5, unit, False),          # 单位
                    (8, location, False),      # 地点
                    (9, cabinet, False),       # 柜号
                    (10, status_text, False)   # 状态
                ]

                for col_idx, text_value, is_advanced in columns_to_process:
                    # 创建 QTableWidgetItem
                    cell_item = QTableWidgetItem(str(text_value))
                    
                    # 设置背景色
                    cell_item.setBackground(color)
                    
                    # 🔍 判断是否需要设置 ToolTip
                    # 逻辑：如果文本的实际像素宽度 > 当前列宽，则设置 ToolTip
                    # 注意：此时列宽可能还没最终确定（因为是 ResizeToContents），
                    # 但我们可以先设置 ToolTip，Qt 会在绘制时再次检查。
                    # 为了保险起见，只要文本非空，我们都设置 ToolTip，
                    # 或者更智能地：仅当文本长度超过一定阈值或列被固定时。
                    
                    # 【策略 A：简单粗暴】只要内容有值，就设置 ToolTip 显示完整内容
                    # 优点：绝对可靠，用户一定能看到全称。
                    # 缺点：鼠标放上去就有提示，可能有点烦。
                    
                    # 【策略 B：智能判断】(推荐) 
                    # 由于 Qt 在 Render 阶段很难精确获取“渲染后的列宽”（因为还在计算中），
                    # 我们采用混合策略：
                    # 1. 名称列：始终使用高级 Tooltip (无论是否截断，因为信息量大)。
                    # 2. 其他列：如果文本长度超过 20 字符，或者该列是固定宽度，则设置 Tooltip。
                    #    或者直接设置：如果文本长度 > 15，就设 Tooltip。
                    
                    should_set_tooltip = False
                    final_tooltip = ""

                    if is_advanced:
                        # 名称列始终使用高级 Tooltip
                        should_set_tooltip = True
                        final_tooltip = advanced_tooltip
                    else:
                        # 其他列：如果文本较长，设置纯文本 Tooltip
                        if len(str(text_value)) > 15: 
                            should_set_tooltip = True
                            final_tooltip = str(text_value)
                        elif col_idx == 8 and location: # 地点列即使短也显示完整路径提示
                             should_set_tooltip = True
                             final_tooltip = f"完整位置：{location} - {cabinet}"
                        elif col_idx == 9 and cabinet:
                             should_set_tooltip = True
                             final_tooltip = f"柜号：{cabinet}"

                    if should_set_tooltip and final_tooltip:
                        cell_item.setToolTip(final_tooltip)

                    # 填入表格
                    self.Inventory_table.setItem(row_index, col_idx, cell_item)

                # 填充其他不需要特殊 Tooltip 的列 (ID, 当前库存, 最小库存)
                self.Inventory_table.setItem(row_index, 0, QTableWidgetItem(str(item['id'])))
                self.Inventory_table.item(row_index, 0).setBackground(color) # ID 也要上色
                
                curr_stock_item = QTableWidgetItem(str(current))
                curr_stock_item.setBackground(color)
                self.Inventory_table.setItem(row_index, 6, curr_stock_item)
                
                min_stock_item = QTableWidgetItem(str(minimum))
                min_stock_item.setBackground(color)
                self.Inventory_table.setItem(row_index, 7, min_stock_item)

                # 隐藏 ID 列
                if row_index == 0:
                    self.Inventory_table.setColumnHidden(0, True)

            self.update_status_label()
            print("🎉 [Render] 数据填充完成。")
            
        finally:
            # 🔥【关键优化 3】恢复界面重绘
            self.Inventory_table.setUpdatesEnabled(True)
            self.Inventory_table.setSortingEnabled(True)
            self.Inventory_table.viewport().update()

    # def _populate_table(self, data):
    #     """填充表格数据 - 【终极增强版：显示同名异型总和及全局分布详情】"""
    #     print(f"⚙️ [Render] 准备渲染 {len(data)} 行数据...")
        
    #     # 🔥【关键优化 1】暂停界面重绘
    #     self.Inventory_table.setUpdatesEnabled(False)
    #     self.Inventory_table.setSortingEnabled(False)
        
    #     try:
    #         self.Inventory_table.setRowCount(len(data))
            
    #         # --- 🌟 新增步骤：深度数据聚合分析 ---
            
    #         # 1. 基础聚合：(name, ref) -> {total_stock, locations_set, cabinets_set}
    #         # 用于显示当前物品的全局分布
    #         global_item_map = {} 
            
    #         # 2. 高级聚合：name -> {ref: stock} 
    #         # 用于计算"同名但不同型号"的库存总和
    #         name_model_map = {} 

    #         for item in data:
    #             name = str(item.get('name', '')).strip()
    #             ref = str(item.get('reference', '')).strip()
    #             loc = str(item.get('location', '')).strip() or "未指定位置"
    #             cab = str(item.get('cabinet', '')).strip() or "无柜号"
                
    #             try:
    #                 stock = int(item.get('current_stock', 0))
    #             except ValueError:
    #                 stock = 0
                
    #             if not name:
    #                 continue

    #             # --- 构建全局物品地图 (Name + Ref) ---
    #             key = (name, ref)
    #             if key not in global_item_map:
    #                 global_item_map[key] = {
    #                     'total': 0,
    #                     'locations': set(),
    #                     'cabinets': set(),
    #                     'unit': item.get('unit', '')
    #                 }
                
    #             global_item_map[key]['total'] += stock
    #             global_item_map[key]['locations'].add(loc)
    #             global_item_map[key]['cabinets'].add(f"{loc}-{cab}") # 记录完整路径

    #             # --- 构建设备名称模型地图 (Name -> {Ref: Stock}) ---
    #             if name not in name_model_map:
    #                 name_model_map[name] = {}
                
    #             if ref not in name_model_map[name]:
    #                 name_model_map[name][ref] = 0
    #             name_model_map[name][ref] += stock
            
    #         # -------------------------------------------------------

    #         # 定义颜色常量
    #         critical_color = QColor(255, 179, 179) # 缺货红
    #         warning_color = QColor(255, 240, 192)  # 预警黄
    #         default_color = QColor(255, 255, 255)  # 正常白
            
    #         for row_index, item in enumerate(data):
    #             # 1. 计算库存状态和颜色
    #             current = item['current_stock']
    #             minimum = item['min_stock']
    #             status_text = "正常"
    #             color = default_color
                
    #             if current <= 0:
    #                 status_text = "缺货"
    #                 color = critical_color
    #             elif current <= minimum:
    #                 status_text = "预警"
    #                 color = warning_color
                
    #             # 2. 构建智能显示名称
    #             name = item['name']
    #             location = item.get('location', '')
    #             cabinet = item.get('cabinet', '')
                
    #             display_name = name
    #             if location:
    #                 display_name += f" 📍[{location}]"
    #             if cabinet:
    #                 display_name += f" 🗄️({cabinet})"
                
    #             # 3. 🌟 构建终极版 ToolTip
    #             ref = item.get('reference', '')
    #             unit = item.get('unit', '')
    #             key = (name, ref)
                
    #             # 获取当前物品的全局数据
    #             current_global = global_item_map.get(key, {'total': 0, 'locations': set(), 'cabinets': set()})
    #             total_stock = current_global['total']
    #             all_locations = sorted(list(current_global['locations']))
    #             all_cabinets = sorted(list(current_global['cabinets']))
                
    #             # 计算"同名不同型号"的总和
    #             other_models_stock = 0
    #             other_models_info = []
    #             if name in name_model_map:
    #                 for other_ref, stock_val in name_model_map[name].items():
    #                     if other_ref != ref:
    #                         other_models_stock += stock_val
    #                         other_models_info.append(f"{other_ref}: {stock_val}")
                
    #             # --- 开始构建 HTML ---
    #             tooltip_parts = []
                
    #             # 头部：基本信息
    #             tooltip_parts.append(f"<div style='font-family: Arial; font-size: 13px;'>")
    #             tooltip_parts.append(f"<b style='font-size: 14px; color: #1976D2;'>📦 {name}</b>")
    #             tooltip_parts.append(f"<br><b>型号:</b> {ref} | <b>单位:</b> {unit}")
    #             tooltip_parts.append(f"<br><b>当前位置:</b> {location or '未指定'} - {cabinet or '无'}")
    #             tooltip_parts.append(f"<br><b>当前库存:</b> <span style='font-weight:bold; font-size:15px;'>{current}</span> {unit}")
                
    #             # 分割线
    #             tooltip_parts.append("<hr style='border: 0; border-top: 1px solid #ddd; margin: 5px 0;'>")
                
    #             # 第一部分：全局总库存 (同名同型号)
    #             if len(all_locations) > 1 or (len(all_locations) == 1 and len(all_cabinets) > 1):
    #                 # 多地/多柜分布
    #                 tooltip_parts.append(f"<b style='color: #D32F2F;'>🌍 全局总库存: {total_stock} {unit}</b>")
    #                 tooltip_parts.append(f"<br><i>(分布在 {len(all_locations)} 个位置，共 {len(all_cabinets)} 个存储点)</i>")
                    
    #                 # 显示具体分布 (限制显示数量以防 tooltip 太长)
    #                 loc_text = ", ".join(all_locations[:5])
    #                 if len(all_locations) > 5: loc_text += f"... (+{len(all_locations)-5})"
    #                 tooltip_parts.append(f"<br><b>📍 涉及位置:</b> {loc_text}")
                    
    #                 cab_text = ", ".join(all_cabinets[:5])
    #                 if len(all_cabinets) > 5: cab_text += f"... (+{len(all_cabinets)-5})"
    #                 tooltip_parts.append(f"<br><b>🗄️ 具体柜号:</b> {cab_text}")
    #             else:
    #                 # 单一位置
    #                 tooltip_parts.append(f"<b style='color: #388E3C;'>✅ 全局总库存: {total_stock} {unit}</b> (唯一记录)")
                
    #             # 分割线
    #             tooltip_parts.append("<hr style='border: 0; border-top: 1px solid #ddd; margin: 5px 0;'>")
                
    #             # 第二部分：同名不同型号统计
    #             if other_models_stock > 0:
    #                 tooltip_parts.append(f"<b style='color: #F57C00;'>🔄 同名其他型号总库存: {other_models_stock} {unit}</b>")
    #                 tooltip_parts.append(f"<br><i>(共 {len(other_models_info)} 种其他型号)</i>")
    #                 # 显示具体型号 (限制显示数量)
    #                 models_preview = ", ".join(other_models_info[:5])
    #                 if len(other_models_info) > 5:
    #                     models_preview += f"... (+{len(other_models_info)-5})"
    #                 tooltip_parts.append(f"<br><b>详情:</b> {models_preview}")
    #             else:
    #                 tooltip_parts.append(f"<i style='color: #999;'>暂无同名其他型号记录</i>")

    #             # 底部分割线
    #             tooltip_parts.append("<hr style='border: 0; border-top: 1px solid #ddd; margin: 5px 0;'>")
                
    #             # 第三部分：属性信息
    #             tooltip_parts.append(f"<b>类别:</b> {item.get('category', '其他')} | <b>专业:</b> {item.get('domain', '其他')}")
    #             tooltip_parts.append(f"<br><b>最小库存警戒线:</b> {minimum}")
    #             tooltip_parts.append("</div>") # 结束 div
                
    #             tooltip_info = "".join(tooltip_parts)

    #             # 4. 填充数据
    #             name_item = QTableWidgetItem(display_name)
    #             name_item.setToolTip(tooltip_info)
    #             self.Inventory_table.setItem(row_index, 1, name_item)
                
    #             # 其他列
    #             self.Inventory_table.setItem(row_index, 0, QTableWidgetItem(str(item['id'])))
    #             self.Inventory_table.setItem(row_index, 2, QTableWidgetItem(ref))
    #             self.Inventory_table.setItem(row_index, 3, QTableWidgetItem(item.get('category', '其他')))
    #             self.Inventory_table.setItem(row_index, 4, QTableWidgetItem(item.get('domain', '其他')))
    #             self.Inventory_table.setItem(row_index, 5, QTableWidgetItem(unit))
    #             self.Inventory_table.setItem(row_index, 6, QTableWidgetItem(str(current)))
    #             self.Inventory_table.setItem(row_index, 7, QTableWidgetItem(str(minimum)))
                
    #             loc_item = QTableWidgetItem(location)
    #             loc_item.setToolTip(f"完整位置: {location} - {cabinet}")
    #             self.Inventory_table.setItem(row_index, 8, loc_item)
                
    #             self.Inventory_table.setItem(row_index, 9, QTableWidgetItem(cabinet))
    #             self.Inventory_table.setItem(row_index, 10, QTableWidgetItem(status_text))
                
    #             # 5. 批量设置背景色
    #             for col in range(self.Inventory_table.columnCount()):
    #                 cell_item = self.Inventory_table.item(row_index, col)
    #                 if cell_item:
    #                     cell_item.setBackground(color)
                
    #             if row_index == 0:
    #                 self.Inventory_table.setColumnHidden(0, True)

    #         self.update_status_label()
    #         print("🎉 [Render] 数据填充完成。")
            
    #     finally:
    #         # 🔥【关键优化 3】恢复界面重绘
    #         self.Inventory_table.setUpdatesEnabled(True)
    #         self.Inventory_table.setSortingEnabled(True)
    #         self.Inventory_table.viewport().update()



    def refresh_data(self):
        """刷新按钮的处理函数：重新从数据库加载数据"""
        self.load_Inventory_data()
        self.status_label.setText(f"数据已刷新 | 总计 {self.Inventory_table.rowCount()} 条记录。")


    def update_status_label(self):
        """更新状态栏，显示总记录数和选中数量"""
        total_count = self.Inventory_table.rowCount()
        selected_count = len(self.Inventory_table.selectionModel().selectedRows())
        
        if selected_count > 0:
            self.status_label.setText(f"总计 {total_count} 条记录，已选中 {selected_count} 条。")
        else:
            self.status_label.setText(f"总计 {total_count} 条记录。")

    def filter_data(self):
        """根据搜索框和筛选下拉框内容过滤表格行"""
        search_text = self.search_input.text().lower().strip()
        category_filter = self.category_filter_combo.currentText()
        domain_filter = self.domain_filter_combo.currentText()
        location_filter = self.location_filter_combo.currentText()
        
        visible_count = 0
        
        for i in range(self.Inventory_table.rowCount()):
            # 获取表格中的数据项
            name_item = self.Inventory_table.item(i, 1)
            ref_item = self.Inventory_table.item(i, 2)
            category_item = self.Inventory_table.item(i, 3)
            domain_item = self.Inventory_table.item(i, 4)
            location_item = self.Inventory_table.item(i, 8) # 地点列
            
            # 获取原始数据 (用于获取准确的 cabinet)
            item_data = self.all_data[i] if i < len(self.all_data) else {}
            cabinet = item_data.get('cabinet', '').lower()
            location_raw = item_data.get('location', '').lower() # 获取原始地点用于搜索

            hide = False
            
            # --- 搜索框筛选逻辑 ---
            if search_text:
                name_match = name_item and search_text in name_item.text().lower()
                ref_match = ref_item and search_text in ref_item.text().lower()
                cabinet_match = search_text in cabinet
                location_match = search_text in location_raw # 【新增】支持搜地点

                # 只要有一个匹配就不隐藏
                if not (name_match or ref_match or cabinet_match or location_match):
                    hide = True
            
            # --- 下拉框筛选逻辑 (保持不变) ---
            if not hide and category_filter != "ALL":
                if not category_item or category_item.text() != category_filter:
                    hide = True
            
            if not hide and domain_filter != "ALL":
                if not domain_item or domain_item.text() != domain_filter:
                    hide = True
            
            if not hide and location_filter != "ALL":
                if not location_item or location_item.text() != location_filter:
                    hide = True
            
            self.Inventory_table.setRowHidden(i, hide)
            
            if not hide:
                visible_count += 1
        
        # 更新状态栏
        total_count = self.Inventory_table.rowCount()
        if visible_count < total_count:
            self.status_label.setText(f"筛选结果：显示 {visible_count} / {total_count} 条记录。")
        else:
            self.status_label.setText(f"总计 {total_count} 条记录。")
            
    # def filter_data(self):
    #     """根据搜索框和筛选下拉框内容过滤表格行"""
    #     search_text = self.search_input.text().lower().strip()
    #     category_filter = self.category_filter_combo.currentText()
    #     domain_filter = self.domain_filter_combo.currentText()
    #     location_filter = self.location_filter_combo.currentText()
        
    #     visible_count = 0
        
    #     for i in range(self.Inventory_table.rowCount()):
    #         name_item = self.Inventory_table.item(i, 1)
    #         ref_item = self.Inventory_table.item(i, 2)
    #         category_item = self.Inventory_table.item(i, 3)
    #         domain_item = self.Inventory_table.item(i, 4)
    #         location_item = self.Inventory_table.item(i, 8)
            
    #         item_data = self.all_data[i] if i < len(self.all_data) else {}
            
    #         # 【修改】只获取合并后的柜号
    #         cabinet = item_data.get('cabinet', '').lower()

    #         hide = False
            
    #         # 搜索框筛选
    #         if search_text:
    #             name_match = name_item and search_text in name_item.text().lower()
    #             ref_match = ref_item and search_text in ref_item.text().lower()
                 
    #             # 【修改】只匹配当前柜号
    #             cabinet_match = search_text in cabinet

    #             if not (name_match or ref_match or cabinet_match):
    #                 hide = True
            
    #         # 类别筛选
    #         if not hide and category_filter != "ALL":
    #             if not category_item or category_item.text() != category_filter:
    #                 hide = True
            
    #         # 专业筛选
    #         if not hide and domain_filter != "ALL":
    #             if not domain_item or domain_item.text() != domain_filter:
    #                 hide = True
            
    #         # 储存位置筛选
    #         if not hide and location_filter != "ALL":
    #             if not location_item or location_item.text() != location_filter:
    #                 hide = True
            
    #         self.Inventory_table.setRowHidden(i, hide)
            
    #         if not hide:
    #             visible_count += 1
        
    #     # 更新状态栏显示筛选结果
    #     total_count = self.Inventory_table.rowCount()
    #     if visible_count < total_count:
    #         self.status_label.setText(f"筛选结果：显示 {visible_count} / {total_count} 条记录。")
    #     else:
    #         self.status_label.setText(f"总计 {total_count} 条记录。")
            
        
    def add_item_dialog(self):
        """显示新增物品对话框"""
        dialog = AddItemDialog(self.db_path, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted: 
            # ❌ 旧代码 (容易卡):
            # self.load_Inventory_data()
            
            # ✅ 新代码 (延迟 300ms 刷新，确保锁释放):
            QTimer.singleShot(300, self.load_Inventory_data)
            
            
    def edit_item_dialog(self):
        """编辑选中物品"""
        selected_rows = self.Inventory_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要编辑的物品行。")
            return
        
        if len(selected_rows) > 1:
            reply = QMessageBox.question(
                self,
                "多选提示",
                f"您选中了 {len(selected_rows)} 个物品。\n\n是否使用批量编辑功能？ \n选择'否'将只编辑第一个选中的物品。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.batch_edit_action()
                return
            
        row_index = selected_rows[0].row()
        
        item_id = int(self.Inventory_table.item(row_index, 0).text())
        # 为了获取准确的 cabinet，从 all_data 取
        item_data = next((item for item in self.all_data if item['id'] == item_id), None)
        
        if not item_data:
             QMessageBox.critical(self, "错误", "无法找到该物品的详细数据。")
             return

        # 构建编辑所需数据字典
        edit_data = {
            'id': item_data['id'],
            'name': item_data['name'],
            'reference': item_data['reference'],
            'category': item_data.get('category', '其他'),
            'domain': item_data.get('domain', '其他'),
            'unit': item_data['unit'],
            'current_stock': item_data['current_stock'],
            'min_stock': item_data['min_stock'],
            'location': item_data['location'],
            'cabinet': item_data.get('cabinet', '')
            # 【修改】移除了 initial_cabinet
        }
        
        # 弹出编辑对话框
        dialog = EditItemDialog(self.db_path, edit_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted: 
            # ❌ 旧代码:
            # self.load_Inventory_data()
            
            # ✅ 新代码:
            QTimer.singleShot(300, self.load_Inventory_data)


    def batch_edit_action(self):
        """批量编辑选中的物品"""
        selected_rows = self.Inventory_table.selectionModel().selectedRows()
        
        if len(selected_rows) == 0:
            QMessageBox.warning(self, "警告", "请先选择要批量编辑的物品。提示：按住Ctrl键点击可以多选。")
            return
        
        if len(selected_rows) == 1:
            reply = QMessageBox.question(self, "单选提示", "您只选中了一个物品。是否使用普通编辑功能？", 
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                        QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.Yes:
                self.edit_item_dialog()
            return
        
        # 收集选中物品的完整信息
        selected_items = []
        for row_model_index in selected_rows:
            row = row_model_index.row()
            item_id = int(self.Inventory_table.item(row, 0).text())
            
            # 从 all_data 中查找完整信息
            item_data = next((item for item in self.all_data if item['id'] == item_id), None)
            
            if item_data:
                selected_items.append({
                    'id': item_data['id'],
                    'name': item_data['name'],
                    'reference': item_data['reference'],
                    'category': item_data.get('category', '其他'),
                    'domain': item_data.get('domain', '其他'),
                    'unit': item_data['unit'],
                    'current_stock': item_data['current_stock'],
                    'min_stock': item_data['min_stock'],
                    'location': item_data['location'],
                    'cabinet': item_data.get('cabinet', '')
                    # 【修改】移除了 initial_cabinet
                })
        
        # 打开批量编辑对话框
        if selected_items:
            dialog = BatchEditDialog(self.db_path, selected_items, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # ❌ 旧代码:
                # self.load_Inventory_data()
                
                # ✅ 新代码:
                QTimer.singleShot(300, self.load_Inventory_data)


    def delete_item_action(self):
        """删除选中物品"""
        selected_rows = self.Inventory_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的物品行。")
            return
        
        # 支持多选删除
        if len(selected_rows) > 1:
            reply = QMessageBox.question(
                self,
                "确认批量删除",
                f"您确定要删除选中的 {len(selected_rows)} 个物品吗？\n\n⚠️ 注意：此操作将同时删除这些物品及其所有相关的交易记录！\n数据不可恢复！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success_count = 0
                failed_count = 0
                
                for row_model_index in selected_rows:
                    row = row_model_index.row()
                    item_id = int(self.Inventory_table.item(row, 0).text())
                    
                    if db_manager.delete_Inventory_item(self.db_path, item_id):
                        success_count += 1
                    else:
                        failed_count += 1
                
                if failed_count == 0:
                    QMessageBox.information(self, "成功", f"成功删除了 {success_count} 个物品及其关联交易记录。")
                else:
                    QMessageBox.warning(self, "部分失败", f"成功删除：{success_count} 个\n失败：{failed_count} 个")
                
                # self.load_Inventory_data()
                QTimer.singleShot(300, self.load_Inventory_data)
            return
            
        # 单个删除
        row_index = selected_rows[0].row()
        item_id = int(self.Inventory_table.item(row_index, 0).text())
        item_name = self.Inventory_table.item(row_index, 1).text()
        
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"您确定要删除物品 **{item_name}** (ID: {item_id}) 吗？\n\n注意：此操作将同时删除该物品及其所有相关的交易记录，数据不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if db_manager.delete_Inventory_item(self.db_path, item_id):
                QMessageBox.information(self, "成功", "物品及关联交易记录已成功删除。")
                # self.load_Inventory_data()
                QTimer.singleShot(300, self.load_Inventory_data)
            else:
                QMessageBox.critical(self, "删除失败", "删除失败！请检查数据库连接或确认该物品ID是否存在。")
    load_inventory_data = load_Inventory_data

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 使用绝对路径测试 (根据您的实际路径调整)
    TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db', 'honsen_storage.db')
    
    if not os.path.exists(TEST_DB_PATH):
        # 如果 db 文件夹下没有，尝试根目录 (兼容旧版)
        TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'honsen_storage.db')
        if not os.path.exists(TEST_DB_PATH):
            print("警告：数据库文件不存在，请先通过 login.py 初始化。")
            # 创建一个空窗口防止崩溃
            window = InventoryPage("") 
            window.show()
            sys.exit(app.exec())

    window = InventoryPage(TEST_DB_PATH)
    window.show()
    sys.exit(app.exec())
    
