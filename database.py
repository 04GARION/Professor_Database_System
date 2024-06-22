# -*- coding: utf-8 -*-
"""
Created on Wed May 15 22:41:25 2024

@author: 28655
"""
import pymysql
from configparser import ConfigParser
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import sys
import xlsxwriter
from datetime import datetime

# 根据表的名称，给出表中出现的键
key_dict={
    'Professor':['Work_ID','Work_Name','Gender','Title'],
    'Essai':['Essai_ID','Essai_Name','Publish_Source','Publish_Date','Essai_Type','Essai_Rank'],
    'Project':['Project_ID','Project_Name','Project_Source','Project_Type','Total_Funding','Start_Date','Finish_Date'],
    'Course':['Course_ID','Course_Name','Course_Hour','Course_Type'],
    'Publish':['Work_ID','Essai_ID','Author_Sequence','Is_Comm_Author'],
    'Undertake':['Work_ID','Project_ID','Undertake_Sequence','Responsible_Funding'],
    'Teach':['Work_ID','Course_ID','Course_Year','Semester','Responsible_Hour']
    }
key_dict_cn={
    'Professor':['工号','姓名','性别','职称'],
    'Essai':['编号','名称','发表源','发表日期','论文类别','论文级别'],
    'Project':['编号','名称','项目来源','项目类型','总资金','起始日期','结束日期'],
    'Course':['编号','名称','课时数','课程性质'],
    'Publish':['工号','论文编号','作者排名','通讯作者'],
    'Undertake':['工号','项目编号','排名','负责资金'],
    'Teach':['工号','课程编号','学年','学期','负责课时数']
    }
key_cn=['教授','论文','项目','课程','发表论文','承担项目','讲授课程']
        
# 根据表的名称，给出表的主键
primary_key_dict={
    'Professor':['Work_ID'],
    'Essai':['Essai_ID'],
    'Project':['Project_ID'],
    'Course':['Course_ID'],
    'Publish':['Work_ID','Essai_ID'],
    'Undertake':['Work_ID','Project_ID'],
    'Teach':['Work_ID','Course_ID','Course_Year','Semester']
    }
    
# 根据表的名称，给出外键所在的表
foreign_table_dict={
    'Publish':['Professor','Essai'],
    'Undertake':['Professor','Project'],
    'Teach':['Professor','Course']
    }

# 职称
titles=[
    '博士后',
    '助教',
    '讲师',
    '副教授',
    '特任教授',
    '教授',
    '助理研究员' ,
    '特任副研究员',
    '副研究员',
    '特任研究员',
    '研究员'
    ]
        
# 性别
genders=['男','女']

# 论文类型
essai_type=[
    'full paper',
    'short paper',
    'poster paper',
    'demo paper'
    ]

# 论文级别
essai_rank=[
    'CCF-A',
    'CCF-B',
    'CCF-C',
    '中文CCF-A',
    '中文CCF-B'
    ]

# 项目类型
project_type=[
    '国家级项目',
    '省部级项目',
    '市厅级项目',
    '企业合作项目',
    '其他类型项目'
    ]

# 课程性质
course_type=[
    '本科生课程',
    '研究生课程'
    ]

# 学期
semesters=[
    '春季学期',
    '夏季学期',
    '秋季学期'
    ]

class PyQtUI(QDialog):
    def __init__(self, parent=None):
        super(PyQtUI, self).__init__(parent)
        
        self.min_year=2000
        self.max_year=QDate.currentDate().year()
        self.year_list=list(range(QDate.currentDate().year(),self.min_year,-1))

        self.db=db_connect()

        self.originalPalette = QApplication.palette()
        self.resize(2000,1500)
        
        self.table=''
        self.condition=''
        self.current_condition=''
        self.keys=[]
        self.values=[]
        self.have_result=0
        
        # 创建更新目录
        # 在保存前的检查，需要根据更新目录中的值，来确定发生过变化的表项
        # 注意依赖一个表的表发生插入或更新时，也应当记录
        self.check_project=[]
        self.check_course=[]
        
        self.use_welcome_layout()
        
    def use_info_message(self,title,message):
        return QMessageBox.information(self,title,message,QMessageBox.Yes)
        
    def use_question_message(self,title,message):
        return QMessageBox.question(self,title,message,QMessageBox.Yes|QMessageBox.No)
    
    def use_warning_message(self,title,message):
        return QMessageBox.warning(self,title,message,QMessageBox.Yes)
    
    def db_reconnect(self):
        self.db=db_connect()
    
    def db_save(self):
        # 保存前需要进行约束检查，如课时总和的检查、资金总和的检查
        state=1
        # 检查总课时数
        l=self.check_course
        for e in l: # 这里是枚举每个需要被检查的课程
            self.current_course_id=e
            
            hour_list=[]
            
            for y in self.year_list:
                for s in semesters:
                    self.current_course_year=y
                    self.current_semester=semesters.index(s)+1
                    self.current_total_hour=0
                    subn,subl=self.select_course_hour()
                    for sube in subl:
                        self.current_total_hour+=sube[key_dict['Teach'].index('Responsible_Hour')]
                        
                    if (self.current_total_hour>0) and (not self.current_total_hour in hour_list):
                        hour_list.append(self.current_total_hour)
                        
            if len(hour_list)>1:
                self.use_warning_message('总课时不符','当前课程的不同次教学安排中出现总课时不一致情况！')
                continue
            elif len(hour_list)==1:
                self.current_total_hour=hour_list[0]
                
            subn,subl=self.select_total_hour()
            if subn>0:
                actual_total_hour=subl[0][key_dict['Course'].index('Course_Hour')]
            
                if actual_total_hour!=self.current_total_hour:
                    ret=self.use_question_message('总课时不符','当前课程出现总课时计算与实际输入课时数的出入。是否重新设定课时数为实际输入课时数的总和？')
                    if ret==QMessageBox.Yes:
                        self.change_total_hour()
                    else:
                        state=0
        # 检查总经费
        l=self.check_project
        for e in l:
            self.current_project_id=e
            self.current_total_funding=0.0
            subn,subl=self.select_project_funding()
            for sube in subl:
                self.current_total_funding+=sube[key_dict['Undertake'].index('Responsible_Funding')]
                
            subn,subl=self.select_total_funding()
            if subn>0:
                actual_total_funding=subl[0][key_dict['Project'].index('Total_Funding')]
            
                if actual_total_funding!=self.current_total_funding:
                    ret=self.use_question_message('总经费不符','当前项目出现总经费计算与实际输入经费的出入。是否重新设定经费为实际输入经费的总和？')
                    if ret==QMessageBox.Yes:
                        self.change_total_funding()
                    else:
                        state=0
        
        if state:
            self.db.commit()
        else:
            self.use_warning_message('保存失败','保存失败！')
    
    def use_welcome_layout(self):
        self.insert_button=QPushButton('插入',self)
        self.insert_button.clicked.connect(self.enter_insert)
        self.insert_button.setVisible(True)
        
        self.select_button=QPushButton('查找',self)
        self.select_button.clicked.connect(self.enter_select)
        self.select_button.setVisible(True)
        
        self.save_button=QPushButton('保存',self)
        self.save_button.clicked.connect(self.db_save)
        self.save_button.setVisible(True)
        
        self.connect_button=QPushButton('重新连接',self)
        self.connect_button.clicked.connect(self.db_reconnect)
        self.connect_button.setVisible(True)
        
        self.table_box=QComboBox(self)
        self.table=''
        self.table_box.addItem('请选择操作对象')
        self.table_box.addItems(key_cn)
        self.table_box.currentIndexChanged.connect(self.welcome_choose_target)
        self.table_box.setVisible(True)
        
        self.insert_button.setGeometry(500,1200,100,40)
        self.select_button.setGeometry(700,1200,100,40)
        self.save_button.setGeometry(900,1200,100,40)
        self.connect_button.setGeometry(1100,1200,150,40)
        self.table_box.setGeometry(1400,1200,240,40)
        
    def remove_welcome_layout(self):
        self.insert_button.setVisible(False)
        self.select_button.setVisible(False)
        self.save_button.setVisible(False)
        self.connect_button.setVisible(False)
        self.table_box.setVisible(False)
        
    def get_input_ID(self,text):
        self.input_id=text
        self.valid=1
        for e in self.input_id:
            if not (e>='a' and e<='z' or e>='A' and e<='Z' or e>='0' and e<='9'):
                self.valid=0
        if len(text)==0:
            self.valid=0
        if self.operation=='update':
            self.input_id_valid_update=self.valid
        else:
            self.input_id_valid=self.valid
            
    def get_input_ID_number(self,text):
        self.input_id=text
        self.valid=1
        for e in self.input_id:
            if not (e>='0' and e<='9'):
                self.valid=0
        if len(text)==0:
            self.valid=0
        if self.valid==1:
            self.input_id_number=int(text)
        if self.operation=='update':
            self.input_id_valid_update=self.valid
        else:
            self.input_id_valid=self.valid
        
    def get_input_name(self,text):
        self.input_name=text
        self.valid=not (self.input_name=='')
        if self.operation=='update':
            self.input_name_valid_update=self.valid
        else:
            self.input_name_valid=self.valid
        
    def get_input_fp_ID(self,text):
        self.input_fp_id=text
        self.valid=1
        for e in self.input_fp_id:
            if not (e>='a' and e<='z' or e>='A' and e<='Z' or e>='0' and e<='9'):
                self.valid=0
        if len(text)==0:
            self.valid=0
        else:
            db=self.db
            table=self.fp_table
            pk=primary_key_dict[table][0]
            condition=pk+'=\''+str(text)+'\''
            
            n,l=select(db,table,condition)
            
            # 插入的方式应当保证单一主键搜索的结果唯一
            if n>0:
                self.fp_output_table.setRowCount(n)
                self.fp_output_table.setColumnCount(len(key_dict_cn[table]))
                self.fp_output_table.setHorizontalHeaderLabels(key_dict_cn[table])
                
                translated=translate_list(l[0],table)
                for i in range(len(key_dict_cn[table])):
                    item=QTableWidgetItem(str(translated[i]))
                    self.fp_output_table.setItem(0,i,item)
        if self.operation=='update':
            self.input_fp_id_valid_update=self.valid
        else:
            self.input_fp_id_valid=self.valid
            
    def get_input_fa_ID(self,text):
        self.input_fa_id=text
        self.valid=1
        for e in self.input_fa_id:
            if not (e>='a' and e<='z' or e>='A' and e<='Z' or e>='0' and e<='9'):
                self.valid=0
        if len(text)==0:
            self.valid=0
        else:
            db=self.db
            table=self.fa_table
            pk=primary_key_dict[table][0]
            condition=pk+'=\''+str(text)+'\''
            
            n,l=select(db,table,condition)
            
            # 插入的方式应当保证单一主键搜索的结果唯一
            if n>0:
                self.fa_output_table.setRowCount(n)
                self.fa_output_table.setColumnCount(len(key_dict_cn[table]))
                self.fa_output_table.setHorizontalHeaderLabels(key_dict_cn[table])
                
                translated=translate_list(l[0],table)
                for i in range(len(key_dict_cn[table])):
                    item=QTableWidgetItem(str(translated[i]))
                    self.fa_output_table.setItem(0,i,item)
        if self.operation=='update':
            self.input_fa_id_valid_update=self.valid
        else:
            self.input_fa_id_valid=self.valid
            
    def get_input_fa_ID_number(self,text):
        self.input_fa_id=text
        self.valid=1
        for e in self.input_fa_id:
            if not (e>='a' and e<='z' or e>='A' and e<='Z' or e>='0' and e<='9'):
                self.valid=0
        if len(text)==0:
            self.valid=0
        if self.valid==1:
            self.input_fa_id_number=int(text)
            
            db=self.db
            table=self.fa_table
            pk=primary_key_dict[table][0]
            condition=pk+'='+text
            
            n,l=select(db,table,condition)
            
            # 插入的方式应当保证单一主键搜索的结果唯一
            if n>0:
                self.fa_output_table.setRowCount(n)
                self.fa_output_table.setColumnCount(len(key_dict_cn[table]))
                self.fa_output_table.setHorizontalHeaderLabels(key_dict_cn[table])
                
                translated=translate_list(l[0],table)
                for i in range(len(key_dict_cn[table])):
                    item=QTableWidgetItem(str(translated[i]))
                    self.fa_output_table.setItem(0,i,item)
        if self.operation=='update':
            self.input_fa_id_valid_update=self.valid
        else:
            self.input_fa_id_valid=self.valid
        
    def swap_gender(self):
        if self.fradio.isChecked():
            self.input_gender=2
        elif self.mradio.isChecked():
            self.input_gender=1
        self.valid=1
        if self.operation=='update':
            self.input_gender_valid_update=self.valid
        else:
            self.input_gender_valid=self.valid
            
    def get_input_title(self,text):
        self.input_title=text
        self.valid=not (text==0)
        if self.operation=='update':
            self.input_title_valid_update=self.valid
        else:
            self.input_title_valid=self.valid
        
    def get_input_source(self,text):
        self.input_source=text
        self.valid=not (text=='')
        if self.operation=='update':
            self.input_source_valid_update=self.valid
        else:
            self.input_source_valid=self.valid
        
    def get_publish_date(self,date):
        year=str(date.year())
        month=str(date.month())
        day=str(date.day())
        self.input_publish_date=year+'/'+month+'/'+day
        self.valid=1
        if self.operation=='update':
            self.input_publish_date_valid_update=self.valid
        else:
            self.input_publish_date_valid=self.valid
        
    def get_input_type(self,text):
        self.input_type=text
        self.valid=not (text==0)
        if self.operation=='update':
            self.input_type_valid_update=self.valid
        else:
            self.input_type_valid=self.valid
        
    def get_input_rank(self,text):
        self.input_rank=text
        self.valid=not (text==0)
        if self.operation=='update':
            self.input_rank_valid_update=self.valid
        else:
            self.input_rank_valid=self.valid
            
    def get_input_year_f(self,text):
        self.valid=1
        for e in text:
            if not (e>='0' and e<='9'):
                self.valid=0
        if len(text)==0:
            self.valid=0
        if self.valid==1:
            year=int(text)
            if year in self.year_list:
                self.year_f=year
            else:
                self.year_f=self.min_year
        
    def get_input_year_t(self,text):
        self.valid=1
        for e in text:
            if not (e>='0' and e<='9'):
                self.valid=0
        if len(text)==0:
            self.valid=0
        if self.valid==1:
            year=int(text)
            if year in self.year_list:
                self.year_t=year
            else:
                self.year_t=self.max_year
        
    def get_input_hour(self,text):
        self.valid=1
        for e in text:
            if not (e>='0' and e<='9'):
                self.valid=0
        if len(text)==0:
            self.valid=0
        if self.valid==1:
            self.input_hour=int(text)
        if self.operation=='update':
            self.input_hour_valid_update=self.valid
        else:
            self.input_hour_valid=self.valid
        
    def swap_course_type(self):
        if self.type_sradio.isChecked():
            self.input_type=1
        elif self.type_bradio.isChecked():
            self.input_type=2
        self.valid=1
        if self.operation=='update':
            self.input_type_valid_update=self.valid
        else:
            self.input_type_valid=self.valid
        
    def get_input_funding(self,text):
        after_dot=0
        self.valid=1
        for e in text:
            if not (e>='0' and e<='9'):
                if e=='.':
                    if after_dot:
                        self.valid=0
                    else:
                        after_dot=1
                else:
                    self.valid=0
        if text=='':
            self.valid=0
        if self.valid:
            self.input_funding=float(text)
        if self.operation=='update':
            self.input_funding_valid_update=self.valid
        else:
            self.input_funding_valid=self.valid
    
    def get_start_date(self,date):
        year=str(date.year())
        month=str(date.month())
        day=str(date.day())
        self.input_start_date=year+'/'+month+'/'+day
        self.valid=1
        if self.operation=='update':
            self.input_start_date_valid_update=self.valid
        else:
            self.input_start_date_valid=self.valid
    
    def get_end_date(self,date):
        year=str(date.year())
        month=str(date.month())
        day=str(date.day())
        self.input_end_date=year+'/'+month+'/'+day
        self.valid=1
        if self.operation=='update':
            self.input_end_date_valid_update=self.valid
        else:
            self.input_end_date_valid=self.valid
        
    def get_author_rank(self,text):
        self.input_author_rank=text
        self.valid=1
        for e in self.input_author_rank:
            if not (e>='0' and e<='9'):
                self.valid=0
        if len(text)==0:
            self.valid=0
        if self.valid==1:
            self.input_author_rank=int(text)
        if self.operation=='update':
            self.input_author_rank_valid_update=self.valid
        else:
            self.input_author_rank_valid=self.valid
            
    def swap_comm_author(self):
        self.input_is_comm_author=self.comm_author_box.isChecked()
        self.valid=1
        if self.operation=='update':
            self.input_is_comm_author_update=self.valid
        else:
            self.input_is_comm_author=self.valid
        
    def get_res_rank(self,text):
        self.input_res_rank=text
        self.valid=1
        for e in self.input_res_rank:
            if not (e>='a' and e<='z' or e>='A' and e<='Z' or e>='0' and e<='9'):
                self.valid=0
        if len(text)==0:
            self.valid=0
        if self.valid==1:
            self.input_res_rank=int(text)
        if self.operation=='update':
            self.input_res_rank_valid_update=self.valid
        else:
            self.input_res_rank_valid=self.valid
    
    def get_input_year(self,text):
        self.input_year=self.year_list[text]
        self.valid=1
        if self.operation=='update':
            self.input_year_valid_update=self.valid
        else:
            self.input_year_valid=self.valid
        
    def get_input_semester(self,text):
        self.input_semester=text+1
        self.valid=1
        if self.operation=='update':
            self.input_semester_valid_update=self.valid
        else:
            self.input_semester_valid=self.valid
        
    def get_gender_choice(self):
        self.gender_choice=[]
        if self.fbox_s.isChecked():
            self.gender_choice.append(2)
        if self.mbox_s.isChecked():
            self.gender_choice.append(1)
        
    def get_gender_condition(self):
        l=[]
        key=['Gender']
        for e in self.gender_choice:
            l+=convert_key_value(key,[e])
        if len(l)>0:
            self.input_gender_valid=1
            self.gender_condition=convert_or_condition(l)
        else:
            self.input_gender_valid=0
            self.gender_condition=''
            
    def get_title_choice(self):
        self.title_choice=[]
        for e in self.title_box_s:
            if e.isChecked():
                self.title_choice.append(self.title_box_s.index(e)+1)
            
    def get_title_condition(self):
        l=[]
        key=['Title']
        for e in self.title_choice:
            l+=convert_key_value(key,[e])
        if len(l)>0:
            self.input_title_valid=1
            self.title_condition=convert_or_condition(l)
        else:
            self.input_title_valid=0
            self.title_condition=''
            
    def get_project_type_choice(self):
        self.project_type_choice=[]
        for e in self.type_box_s:
            if e.isChecked():
                self.project_type_choice.append(self.type_box_s.index(e)+1)
    
    def get_essai_type_choice(self):
        self.essai_type_choice=[]
        for e in self.type_box_s:
            if e.isChecked():
                self.essai_type_choice.append(self.type_box_s.index(e)+1)
                
    def get_semester_choice(self):
        self.semester_choice=[]
        for e in self.semester_box_s:
            if e.isChecked():
                self.semester_choice.append(self.semester_box_s.index(e)+1)
                
    def get_semester_condition(self):
        l=[]
        key=['Semester']
        for e in self.semester_choice:
            l+=convert_key_value(key,[e])
        if len(l)>0:
            self.input_semester_valid=1
            self.semester_condition=convert_or_condition(l)
        else:
            self.input_semester_valid=0
            self.semester_condition=''
            
    def get_essai_type_condition(self):
        l=[]
        key=['Essai_Type']
        for e in self.essai_type_choice:
            l+=convert_key_value(key,[e])
        if len(l)>0:
            self.input_type_valid=1
            self.essai_type_condition=convert_or_condition(l)
        else:
            self.input_type_valid=0
            self.essai_type_condition=''
    
    def get_essai_rank_choice(self):
        self.essai_rank_choice=[]
        for e in self.rank_box_s:
            if e.isChecked():
                self.essai_rank_choice.append(self.rank_box_s.index(e)+1)
            
    def get_essai_rank_condition(self):
        l=[]
        key=['Essai_Rank']
        for e in self.essai_rank_choice:
            l+=convert_key_value(key,[e])
        if len(l)>0:
            self.input_rank_valid=1
            self.essai_rank_condition=convert_or_condition(l)
        else:
            self.input_rank_valid=0
            self.essai_rank_condition=''
    
    def get_max_publish_date(self,date):
        year=str(date.year())
        month=str(date.month())
        day=str(date.day())
        self.input_max_publish_date=year+'/'+month+'/'+day
        self.input_max_publish_date_valid=1
    
    def get_min_publish_date(self,date):
        year=str(date.year())
        month=str(date.month())
        day=str(date.day())
        self.input_min_publish_date=year+'/'+month+'/'+day
        self.input_min_publish_date_valid=1
            
    def get_publish_date_condition(self):
        l=[]
        key=['Publish_Date']
        if self.input_min_publish_date_valid:
            l.append(key[0]+'>=\''+self.input_min_publish_date+'\'')
        if self.input_max_publish_date_valid:
            l.append(key[0]+'<=\''+self.input_max_publish_date+'\'')
        if len(l)>0:
            self.input_publish_date_valid=1
            self.publish_date_condition=convert_and_condition(l)
        else:
            self.input_publish_date_valid=0
            self.publish_date_condition=''
            
    def get_project_type_choice(self):
        self.project_type_choice=[]
        for e in self.type_box_s:
            if e.isChecked():
                self.project_type_choice.append(self.type_box_s.index(e)+1)
                
    def get_project_type_condition(self):
        l=[]
        key=['Project_Type']
        for e in self.project_type_choice:
            l+=convert_key_value(key,[e])
        if len(l)>0:
            self.input_type_valid=1
            self.project_type_condition=convert_or_condition(l)
        else:
            self.input_type_valid=0
            self.project_type_condition=''
        
    def get_input_min_funding(self,text):
        after_dot=0
        self.input_min_funding_valid=1
        for e in text:
            if not (e>='0' and e<='9'):
                if e=='.':
                    if after_dot:
                        self.input_min_funding_valid=0
                    else:
                        after_dot=1
                else:
                    self.input_min_funding_valid=0
        if text=='':
            self.input_min_funding_valid=0
        if self.input_min_funding_valid:
            self.input_min_funding=float(text)
        
    def get_input_max_funding(self,text):
        after_dot=0
        self.input_max_funding_valid=1
        for e in text:
            if not (e>='0' and e<='9'):
                if e=='.':
                    if after_dot:
                        self.input_max_funding_valid=0
                    else:
                        after_dot=1
                else:
                    self.input_max_funding_valid=0
        if text=='':
            self.input_max_funding_valid=0
        if self.input_max_funding_valid:
            self.input_max_funding=float(text)
            
    def get_funding_condition(self):
        l=[]
        key=['Total_Funding']
        if self.input_min_funding_valid:
            l.append(key[0]+'>='+str(self.input_min_funding))
        if self.input_max_funding_valid:
            l.append(key[0]+'<='+str(self.input_max_funding))
        if len(l)>0:
            self.input_funding_valid=1
            self.funding_condition=convert_and_condition(l)
        else:
            self.input_funding_valid=0
            self.funding_condition=''
        
    def get_min_author_rank(self,text):
        self.input_min_author_rank=text
        self.input_min_author_rank_valid=1
        for e in self.input_min_author_rank:
            if not (e>='0' and e<='9'):
                self.input_min_author_rank_valid=0
        if len(text)==0:
            self.input_min_author_rank_valid=0
        if self.input_min_author_rank_valid==1:
            self.input_min_author_rank=int(text)
        
    def get_max_author_rank(self,text):
        self.input_max_author_rank=text
        self.input_max_author_rank_valid=1
        for e in self.input_max_author_rank:
            if not (e>='0' and e<='9'):
                self.input_max_author_rank_valid=0
        if len(text)==0:
            self.input_max_author_rank_valid=0
        if self.input_max_author_rank_valid==1:
            self.input_max_author_rank=int(text)
            
    def get_author_rank_condition(self):
        l=[]
        key=['Author_Sequence']
        if self.input_min_author_rank_valid:
            l.append(key[0]+'>='+str(self.input_min_author_rank))
        if self.input_max_author_rank_valid:
            l.append(key[0]+'<='+str(self.input_max_author_rank))
        if len(l)>0:
            self.input_author_rank_valid=1
            self.author_rank_condition=convert_and_condition(l)
        else:
            self.input_author_rank_valid=0
            self.author_rank_condition=''
        
    def get_min_res_rank(self,text):
        self.input_min_res_rank=text
        self.input_min_res_rank_valid=1
        for e in self.input_min_res_rank:
            if not (e>='0' and e<='9'):
                self.input_min_res_rank_valid=0
        if len(text)==0:
            self.input_min_res_rank_valid=0
        if self.input_min_res_rank_valid==1:
            self.input_min_res_rank=int(text)
        
    def get_max_res_rank(self,text):
        self.input_max_res_rank=text
        self.input_max_res_rank_valid=1
        for e in self.input_max_res_rank:
            if not (e>='0' and e<='9'):
                self.input_max_res_rank_valid=0
        if len(text)==0:
            self.input_max_res_rank_valid=0
        if self.input_max_res_rank_valid==1:
            self.input_max_res_rank=int(text)
            
    def get_res_rank_condition(self):
        l=[]
        key=['Undertake_Sequence']
        if self.input_min_res_rank_valid:
            l.append(key[0]+'>='+str(self.input_min_author_rank))
        if self.input_max_res_rank_valid:
            l.append(key[0]+'<='+str(self.input_max_author_rank))
        if len(l)>0:
            self.input_res_rank_valid=1
            self.res_rank_condition=convert_and_condition(l)
        else:
            self.input_res_rank_valid=0
            self.res_rank_condition=''
            
    def get_min_res_hour(self,text):
        self.input_min_res_hour=text
        self.input_min_res_hour_valid=1
        for e in self.input_min_res_hour:
            if not (e>='0' and e<='9'):
                self.input_min_res_hour_valid=0
        if len(text)==0:
            self.input_min_res_hour_valid=0
        if self.input_min_res_hour_valid==1:
            self.input_min_res_hour=int(text)
        
    def get_max_res_hour(self,text):
        self.input_max_res_hour=text
        self.input_max_res_hour_valid=1
        for e in self.input_max_res_hour:
            if not (e>='0' and e<='9'):
                self.input_max_res_hour_valid=0
        if len(text)==0:
            self.input_max_res_hour_valid=0
        if self.input_max_res_hour_valid==1:
            self.input_max_res_hour=int(text)
            
    def get_res_hour_condition(self):
        l=[]
        key=['Responsible_Hour']
        if self.input_min_res_hour_valid:
            l.append(key[0]+'>='+str(self.input_min_author_hour))
        if self.input_max_res_hour_valid:
            l.append(key[0]+'<='+str(self.input_max_author_hour))
        if len(l)>0:
            self.input_res_hour_valid=1
            self.res_hour_condition=convert_and_condition(l)
        else:
            self.input_res_hour_valid=0
            self.res_hour_condition=''
            
    def get_min_res_funding(self,text):
        after_dot=0
        self.input_min_res_funding_valid=1
        for e in text:
            if not (e>='0' and e<='9'):
                if e=='.':
                    if after_dot:
                        self.input_min_res_funding_valid=0
                    else:
                        after_dot=1
                else:
                    self.input_min_res_funding_valid=0
        if text=='':
            self.input_min_res_funding_valid=0
        if self.input_min_res_funding_valid:
            self.input_min_res_funding=float(text)
        
    def get_max_res_funding(self,text):
        after_dot=0
        self.input_max_res_funding_valid=1
        for e in text:
            if not (e>='0' and e<='9'):
                if e=='.':
                    if after_dot:
                        self.input_max_res_funding_valid=0
                    else:
                        after_dot=1
                else:
                    self.input_max_res_funding_valid=0
        if text=='':
            self.input_max_res_funding_valid=0
        if self.input_max_res_funding_valid:
            self.input_max_res_funding=float(text)
            
    def get_res_funding_condition(self):
        l=[]
        key=['Responsible_Funding']
        if self.input_min_res_funding_valid:
            l.append(key[0]+'>='+str(self.input_min_res_funding))
        if self.input_max_res_funding_valid:
            l.append(key[0]+'<='+str(self.input_max_res_funding))
        if len(l)>0:
            self.input_res_funding_valid=1
            self.res_funding_condition=convert_and_condition(l)
        else:
            self.input_res_funding_valid=0
            self.res_funding_condition=''
    
    def get_max_start_date(self,date):
        year=str(date.year())
        month=str(date.month())
        day=str(date.day())
        self.input_max_start_date=year+'/'+month+'/'+day
        self.input_max_start_date_valid=1

    def get_min_start_date(self,date):
        year=str(date.year())
        month=str(date.month())
        day=str(date.day())
        self.input_min_start_date=year+'/'+month+'/'+day
        self.input_min_start_date_valid=1
    
    def get_max_end_date(self,date):
        year=str(date.year())
        month=str(date.month())
        day=str(date.day())
        self.input_max_end_date=year+'/'+month+'/'+day
        self.input_max_end_date_valid=1
    
    def get_min_end_date(self,date):
        year=str(date.year())
        month=str(date.month())
        day=str(date.day())
        self.input_min_end_date=year+'/'+month+'/'+day
        self.input_min_end_date_valid=1
            
    def get_start_date_condition(self):
        l=[]
        key=['Start_Date']
        if self.input_min_start_date_valid:
            l.append(key[0]+'>=\''+self.input_min_start_date+'\'')
        if self.input_max_start_date_valid:
            l.append(key[0]+'<=\''+self.input_max_start_date+'\'')
        if len(l)>0:
            self.input_start_date_valid=1
            self.start_date_condition=convert_and_condition(l)
        else:
            self.input_start_date_valid=0
            self.start_date_condition=''
            
    def get_end_date_condition(self):
        l=[]
        key=['Finish_Date']
        if self.input_min_end_date_valid:
            l.append(key[0]+'>=\''+self.input_min_end_date+'\'')
        if self.input_max_end_date_valid:
            l.append(key[0]+'<=\''+self.input_max_end_date+'\'')
        if len(l)>0:
            self.input_end_date_valid=1
            self.end_date_condition=convert_and_condition(l)
        else:
            self.input_end_date_valid=0
            self.end_date_condition=''
            
    def get_course_type_choice(self):
        self.course_type_choice=[]
        if self.type_sbox_s.isChecked():
            self.course_type_choice.append(1)
        if self.type_bbox_s.isChecked():
            self.course_type_choice.append(2)
            
    def get_course_type_condition(self):
        l=[]
        key=['Course_Type']
        for e in self.course_type_choice:
            l+=convert_key_value(key,[e])
        if len(l)>0:
            self.input_type_valid=1
            self.course_type_condition=convert_or_condition(l)
        else:
            self.input_type_valid=0
            self.course_type_condition=''
        
    def insert_professor(self):
        pk=self.check_insert_primary_key([self.input_id],self.input_id_valid)
        if not pk:
            self.use_warning_message('警告','非法的主键！')
            return
        self.values=[]
        valid=1
        if self.input_id_valid:
            self.values.append(self.input_id)
        else:
            self.values.append('None')
            valid=0
        if self.input_name_valid:
            self.values.append(self.input_name)
        else:
            self.values.append('None')
            valid=0
        if self.input_gender_valid:
            self.values.append(self.input_gender)
        else:
            self.values.append('None')
            valid=0
        if self.input_title_valid:
            self.values.append(self.input_title)
        else:
            self.values.append('None')
            valid=0
            
        if not valid:
            ret=self.use_question_message('信息缺失','有部分信息未填写或无效。确定仍然要插入吗？')
            if ret==QMessageBox.No:
                return
        
        self.UI_action()
        
    def select_professor(self):
        self.keys=[]
        self.values=[]
        if self.input_id_valid:
            self.keys.append('Work_ID')
            self.values.append(self.input_id)
        if self.input_name_valid:
            self.keys.append('Work_Name')
            self.values.append(self.input_name)
            
        l=convert_key_value(self.keys,self.values)
        
        self.get_gender_condition()
        self.get_title_condition()
        
        if self.input_gender_valid:
            l.append(self.gender_condition)
        if self.input_title_valid:
            l.append(self.title_condition)
            
        self.condition=convert_and_condition(l)
        
        self.UI_action()
    
    def update_professor(self):
        pk=self.check_insert_primary_key([self.input_id],self.input_id_valid_update)
        if (not pk) and (self.input_id_valid_update):
            self.use_warning_message('警告','非法的主键！')
            return
        self.keys=[]
        self.values=[]
        if self.input_id_valid_update:
            self.keys.append('Work_ID')
            self.values.append(self.input_id)
        if self.input_name_valid_update:
            self.keys.append('Work_Name')
            self.values.append(self.input_name)
        if self.input_gender_valid_update:
            self.keys.append('Gender')
            self.values.append(self.input_gender)
        if self.input_title_valid_update:
            self.keys.append('Title')
            self.values.append(self.input_title)
        
        self.UI_action()
        
        self.operation='select'
        self.UI_action()
        
        self.operation='update'
        
    def insert_essai(self):
        pk=self.check_insert_primary_key([self.input_id_number],self.input_id_valid)
        if not pk:
            self.use_warning_message('警告','非法的主键！')
            return
        self.values=[]
        valid=1
        if self.input_id_valid:
            self.values.append(self.input_id_number)
        else:
            self.values.append('None')
            valid=0
        if self.input_name_valid:
            self.values.append(self.input_name)
        else:
            self.values.append('None')
            valid=0
        if self.input_source_valid:
            self.values.append(self.input_source)
        else:
            self.values.append('None')
            valid=0
        if self.input_publish_date_valid:
            self.values.append(self.input_publish_date)
        else:
            self.values.append('None')
            valid=0
        if self.input_type_valid:
            self.values.append(self.input_type)
        else:
            self.values.append('None')
            valid=0
        if self.input_rank_valid:
            self.values.append(self.input_rank)
        else:
            self.values.append('None')
            valid=0
        
        if not valid:
            ret=self.use_question_message('信息缺失','有部分信息未填写或无效。确定仍然要插入吗？')
            if ret==QMessageBox.No:
                return
        
        self.UI_action()
        
    def select_essai(self):
        self.keys=[]
        self.values=[]
        if self.input_id_valid:
            self.keys.append('Essai_ID')
            self.values.append(self.input_id_number)
        if self.input_name_valid:
            self.keys.append('Essai_Name')
            self.values.append(self.input_name)
        if self.input_source_valid:
            self.keys.append('Publish_Source')
            self.values.append(self.input_source)
        
        l=convert_key_value(self.keys,self.values)
        
        self.get_publish_date_condition()
        self.get_essai_type_condition()
        self.get_essai_rank_condition()
        
        if self.input_publish_date_valid:
            l.append(self.publish_date_condition)
        if self.input_type_valid:
            l.append(self.essai_type_condition)
        if self.input_rank_valid:
            l.append(self.essai_rank_condition)
            
        self.condition=convert_and_condition(l)
        
        self.UI_action()
    
    def update_essai(self):
        pk=self.check_insert_primary_key([self.input_id_number],self.input_id_valid_update)
        if (not pk) and (self.input_id_valid_update):
            self.use_warning_message('警告','非法的主键！')
            return
        self.keys=[]
        self.values=[]
        if self.input_id_valid_update:
            self.keys.append('Essai_ID')
            self.values.append(self.input_id_number)
        if self.input_name_valid_update:
            self.keys.append('Essai_Name')
            self.values.append(self.input_name)
        if self.input_source_valid_update:
            self.keys.append('Publish_Source')
            self.values.append(self.input_source)
        if self.input_publish_date_valid_update:
            self.keys.append('Publish_Date')
            self.values.append(self.input_publish_date)
        if self.input_type_valid_update:
            self.keys.append('Essai_Type')
            self.values.append(self.input_type)
        if self.input_rank_valid_update:
            self.keys.append('Essai_Rank')
            self.values.append(self.input_rank)
        
        self.UI_action()
        
        self.operation='select'
        self.UI_action()
        
        self.operation='update'
        
    def insert_project(self):
        pk=self.check_insert_primary_key([self.input_id],self.input_id_valid)
        if not pk:
            self.use_warning_message('警告','非法的主键！')
            return
        self.values=[]
        valid=1
        if self.input_id_valid:
            self.values.append(self.input_id)
        else:
            self.values.append('None')
            valid=0
        if self.input_name_valid:
            self.values.append(self.input_name)
        else:
            self.values.append('None')
            valid=0
        if self.input_source_valid:
            self.values.append(self.input_source)
        else:
            self.values.append('None')
            valid=0
        if self.input_type_valid:
            self.values.append(self.input_type)
        else:
            self.values.append('None')
            valid=0
        if self.input_funding_valid:
            self.values.append(self.input_funding)
        else:
            self.values.append('None')
            valid=0
        if self.input_start_date_valid:
            self.values.append(self.input_start_date)
        else:
            self.values.append('None')
            valid=0
        if self.input_end_date_valid:
            self.values.append(self.input_end_date)
        else:
            self.values.append('None')
            valid=0
        
        if not valid:
            ret=self.use_question_message('信息缺失','有部分信息未填写或无效。确定仍然要插入吗？')
            if ret==QMessageBox.No:
                return
        
        if not (self.input_id in self.check_project):
            self.check_project.append(self.input_id)
        
        self.UI_action()
        
    def select_project(self):
        self.keys=[]
        self.values=[]
        if self.input_id_valid:
            self.keys.append('Project_ID')
            self.values.append(self.input_id)
        if self.input_name_valid:
            self.keys.append('Project_Name')
            self.values.append(self.input_name)
        if self.input_source_valid:
            self.keys.append('Project_Source')
            self.values.append(self.input_source)
        
        l=convert_key_value(self.keys,self.values)
        
        self.get_project_type_condition()
        self.get_funding_condition()
        self.get_start_date_condition()
        self.get_end_date_condition()
        
        if self.input_type_valid:
            l.append(self.project_type_condition)
        if self.input_funding_valid:
            l.append(self.funding_condition)
        if self.input_start_date_valid:
            l.append(self.start_date_condition)
        if self.input_end_date_valid:
            l.append(self.end_date_condition)
            
        self.condition=convert_and_condition(l)
        
        self.UI_action()
        
    def update_project(self):
        pk=self.check_insert_primary_key([self.input_id],self.input_id_valid_update)
        if (not pk) and (self.input_id_valid_update):
            self.use_warning_message('警告','非法的主键！')
            return
        self.keys=[]
        self.values=[]
        if self.input_id_valid_update:
            self.keys.append('Project_ID')
            self.values.append(self.input_id)
        if self.input_name_valid_update:
            self.keys.append('Project_Name')
            self.values.append(self.input_name)
        if self.input_source_valid_update:
            self.keys.append('Project_Source')
            self.values.append(self.input_source)
        if self.input_type_valid_update:
            self.keys.append('Project_Type')
            self.values.append(self.input_type)
        if self.input_funding_valid_update:
            self.keys.append('Total_Funding')
            self.values.append(self.input_funding)
        if self.input_start_date_valid_update:
            self.keys.append('Start_Date')
            self.values.append(self.input_start_date)
        if self.input_end_date_valid_update:
            self.keys.append('Finish_Date')
            self.values.append(self.input_end_date)
            
        db=self.db
        table=self.table
        condition=self.current_condition
        
        n,l=select(db,table,condition)
        
        for e in l:
            current_id=e[key_dict[table].index('Project_ID')]
            if not (current_id in self.check_project):
                self.check_project.append(current_id)
        
        current_id=self.input_id
        if self.input_id_valid_update and (not current_id in self.check_project):
            self.check_project.append(current_id)
        
        self.UI_action()
        
        self.operation='select'
        self.UI_action()
        
        self.operation='update'
        
    def insert_course(self):
        pk=self.check_insert_primary_key([self.input_id],self.input_id_valid)
        if not pk:
            self.use_warning_message('警告','非法的主键！')
            return
        self.values=[]
        valid=1
        if self.input_id_valid:
            self.values.append(self.input_id)
        else:
            self.values.append('None')
            valid=0
        if self.input_name_valid:
            self.values.append(self.input_name)
        else:
            self.values.append('None')
            valid=0
        if self.input_hour_valid:
            self.values.append(self.input_hour)
        else:
            self.values.append('None')
            valid=0
        if self.input_type_valid:
            self.values.append(self.input_type)
        else:
            self.values.append('None')
            valid=0
            
        if not valid:
            ret=self.use_question_message('信息缺失','有部分信息未填写或无效。确定仍然要插入吗？')
            if ret==QMessageBox.No:
                return
        
        if not (self.input_id in self.check_course):
            self.check_course.append(self.input_id)
        
        self.UI_action()
        
    def select_course(self):
        self.keys=[]
        self.values=[]
        if self.input_id_valid:
            self.keys.append('Course_ID')
            self.values.append(self.input_id)
        if self.input_name_valid:
            self.keys.append('Course_Name')
            self.values.append(self.input_name)
        if self.input_hour_valid:
            self.keys.append('Course_Hour')
            self.values.append(self.input_hour)
            
        l=convert_key_value(self.keys,self.values)
        
        self.get_course_type_condition()
        
        if self.input_type_valid:
            l.append(self.course_type_condition)
            
        self.condition=convert_and_condition(l)
        
        self.UI_action()
        
    def update_course(self):
        pk=self.check_insert_primary_key([self.input_id],self.input_id_valid_update)
        if (not pk) and (self.input_id_valid_update):
            self.use_warning_message('警告','非法的主键！')
            return
        self.keys=[]
        self.values=[]
        if self.input_id_valid_update:
            self.keys.append('Course_ID')
            self.values.append(self.input_id)
        if self.input_name_valid_update:
            self.keys.append('Course_Name')
            self.values.append(self.input_name)
        if self.input_hour_valid_update:
            self.keys.append('Course_Hour')
            self.values.append(self.input_hour)
        if self.input_type_valid_update:
            self.keys.append('Course_Type')
            self.values.append(self.input_type)
            
        db=self.db
        table=self.table
        condition=self.current_condition
        
        n,l=select(db,table,condition)
        
        for e in l:
            current_id=e[key_dict[table].index('Course_ID')]
            if not (current_id in self.check_course):
                self.check_course.append(current_id)
                
        current_id=self.input_id
        if self.input_id_valid_update and (not current_id in self.check_course):
            self.check_course.append(current_id)
        
        self.UI_action()
        
        self.operation='select'
        self.UI_action()
        
        self.operation='update'
        
    def insert_publish(self):
        pk=self.check_insert_primary_key([self.input_fp_id,self.input_fa_id_number],self.input_fp_id_valid and self.input_fa_id_valid)
        if not pk:
            self.use_warning_message('警告','非法的主键！')
            return
        fk=self.check_insert_foreign_key([self.input_fp_id,self.input_fa_id_number],self.input_fp_id_valid and self.input_fa_id_valid)
        if not fk:
            self.use_warning_message('警告','非法的外键！')
            return
        self.values=[]
        valid=1
        if self.input_fp_id_valid:
            self.values.append(self.input_fp_id)
        else:
            self.values.append('None')
            valid=0
        if self.input_fa_id_valid:
            self.values.append(self.input_fa_id_number)
        else:
            self.values.append('None')
            valid=0
        if self.input_author_rank_valid:
            self.values.append(self.input_author_rank)
        else:
            self.values.append('None')
            valid=0
        if self.input_is_comm_author_valid:
            self.values.append(self.input_is_comm_author)
        else:
            self.values.append('None')
            valid=0
            
        if not valid:
            ret=self.use_question_message('信息缺失','有部分信息未填写或无效。确定仍然要插入吗？')
            if ret==QMessageBox.No:
                return
        
        self.current_essai_id=self.input_fa_id_number
        self.current_rank=self.input_author_rank
        n=0
        if self.input_author_rank_valid:
            n,l=self.select_author_rank()
        
        if n>0:
            ret=self.use_warning_message('已存在同排名作者！','当前排名发生重复，请重新输入！')
            return
            
        n=0
        # print(self.input_is_comm_author)
        if self.input_is_comm_author_valid and self.input_is_comm_author==1:
            n,l=self.select_comm_author()
        
        if n>0:
            ret=self.use_question_message('已存在通讯作者！','是否要将当前教授设置为新的通讯作者？')
            if ret==QMessageBox.Yes:
                self.org_work_id=l[0][key_dict['Publish'].index('Work_ID')]
                self.conflict_essai_id=self.current_essai_id
                self.change_comm_author()
            else:
                return
        
        self.UI_action()
        
    def update_publish(self):
        db=self.db
        table=self.table
        condition=self.current_condition
        
        n,l=select(db,table,condition)
        
        pk=True
        for e in l:
            input_fp_id=self.input_fp_id if self.input_fp_id_valid_update else e[e[key_dict[table].index('Essai_ID')]]
            input_fa_id_number=self.input_fa_id_number if self.input_fa_id_valid_update else e[key_dict[table].index('Essai_ID')]
            fp_id_valid=self.input_fp_id_valid_update or self.input_fp_id_valid
            fa_id_valid=self.input_fa_id_valid_update or self.input_fa_id_valid
            pk=pk and self.check_insert_primary_key([input_fp_id,input_fa_id_number],fp_id_valid and fa_id_valid)
            
            self.current_essai_id=e[key_dict[table].index('Essai_ID')]
            self.current_rank=self.input_author_rank
            if self.input_author_rank_valid_update:
                n=0
                if self.input_author_rank_valid:
                    n,l=self.select_author_rank()
                
                if n>0:
                    ret=self.use_warning_message('已存在同排名作者！','当前排名发生重复，请重新输入！')
                    return
                
            n=0
            if self.input_is_comm_author_valid_update and self.input_is_comm_author==1:
                n,l=self.select_comm_author()
                
            # print(l[0][e[key_dict[table].index('Work_ID')]])
            # print(e[e[key_dict[table].index('Work_ID')]])
            
            if n>0:
                if l[0][key_dict[table].index('Work_ID')]!=e[key_dict[table].index('Work_ID')]:
                    self.use_warning_message('已存在通讯作者！','重复设置了通讯作者！')
                    return
        if (not pk) and (self.input_fp_id_valid_update and self.input_fa_id_valid_update):
            self.use_warning_message('警告','存在非法的主键！')
            return
        self.keys=[]
        self.values=[]
        if self.input_fp_id_valid_update:
            self.keys.append('Work_ID')
            self.values.append(self.input_fp_id)
        if self.input_fa_id_valid_update:
            self.keys.append('Essai_ID')
            self.values.append(self.input_fa_id_number)
        if self.input_author_rank_valid_update:
            self.keys.append('Author_Sequence')
            self.values.append(self.input_author_rank)
        if self.input_is_comm_author_valid_update:
            self.keys.append('Is_Comm_Author')
            self.values.append(self.input_is_comm_author)
        
        self.UI_action()
        
        self.operation='select'
        self.UI_action()
        
        self.operation='update'
        
    def select_publish(self):
        self.keys=[]
        self.values=[]
        if self.input_fp_id_valid:
            self.keys.append('Work_ID')
            self.values.append(self.input_fp_id)
        if self.input_fa_id_valid:
            self.keys.append('Essai_ID')
            self.values.append(self.input_fa_id_number)
        if self.input_is_comm_author_valid:
            self.keys.append('Is_Comm_Author')
            self.values.append(self.input_is_comm_author)
            
        l=convert_key_value(self.keys,self.values)
        
        self.get_author_rank_condition()
        
        if self.input_author_rank_valid:
            l.append(self.author_rank_condition)
            
        self.condition=convert_and_condition(l)
        
        self.UI_action()
        
    def insert_undertake(self):
        pk=self.check_insert_primary_key([self.input_fp_id,self.input_fa_id],self.input_fp_id_valid and self.input_fa_id_valid)
        if not pk:
            self.use_warning_message('警告','非法的主键！')
            return
        fk=self.check_insert_foreign_key([self.input_fp_id,self.input_fa_id],self.input_fp_id_valid and self.input_fa_id_valid)
        if not fk:
            self.use_warning_message('警告','非法的外键！')
            return
        self.values=[]
        valid=1
        if self.input_fp_id_valid:
            self.values.append(self.input_fp_id)
        else:
            self.values.append('None')
            valid=0
        if self.input_fa_id_valid:
            self.values.append(self.input_fa_id)
        else:
            self.values.append('None')
            valid=0
        if self.input_res_rank_valid:
            self.values.append(self.input_res_rank)
        else:
            self.values.append('None')
            valid=0
        if self.input_funding_valid:
            self.values.append(self.input_funding)
        else:
            self.values.append('None')
            valid=0
            
        if not valid:
            ret=self.use_question_message('信息缺失','有部分信息未填写或无效。确定仍然要插入吗？')
            if ret==QMessageBox.No:
                return
            
        self.current_project_id=self.input_fp_id
        self.current_rank=self.input_res_rank
        n=0
        if self.input_res_rank_valid:
            n,l=self.select_res_rank()
        
        if n>0:
            ret=self.use_warning_message('已存在同排名的承担教授！','当前排名发生重复，请重新输入！')
            return
        
        if not (self.input_fa_id in self.check_project):
            self.check_project.append(self.input_fa_id)
        
        self.UI_action()
        
    def update_undertake(self):
        db=self.db
        table=self.table
        condition=self.current_condition
        
        n,l=select(db,table,condition)
        
        pk=True
        for e in l:
            input_fp_id=self.input_fp_id if self.input_fp_id_valid_update else e[key_dict[table].index('Work_ID')]
            input_fa_id=self.input_fa_id if self.input_fa_id_valid_update else e[key_dict[table].index('Project_ID')]
            fp_id_valid=self.input_fp_id_valid_update or self.input_fp_id_valid
            fa_id_valid=self.input_fa_id_valid_update or self.input_fa_id_valid
            pk=pk and self.check_insert_primary_key([input_fp_id,input_fa_id],fp_id_valid and fa_id_valid)
        if (not pk) and (self.input_fp_id_valid_update and self.input_fa_id_valid_update):
            self.use_warning_message('警告','存在非法的主键！')
            return
        self.keys=[]
        self.values=[]
        if self.input_fp_id_valid_update:
            self.keys.append('Work_ID')
            self.values.append(self.input_fp_id)
        if self.input_fa_id_valid_update:
            self.keys.append('Project_ID')
            self.values.append(self.input_fa_id)
        if self.input_res_rank_valid_update:
            self.keys.append('Undertake_Sequence')
            self.values.append(self.input_res_rank)
        if self.input_funding_valid_update:
            self.keys.append('Responsible_Funding')
            self.values.append(self.input_funding)
            
        db=self.db
        table=self.table
        condition=self.current_condition
        
        n,l=select(db,table,condition)
        
        for e in l:
            current_id=e[key_dict[table].index('Project_ID')]
            if not (current_id in self.check_project):
                self.check_project.append(current_id)
        
        current_id=self.input_fa_id
        if self.input_fa_id_valid_update and (not current_id in self.check_project):
            self.check_project.append(current_id)
        
        self.UI_action()
        
        self.operation='select'
        self.UI_action()
        
        self.operation='update'
        
    def select_undertake(self):
        self.keys=[]
        self.values=[]
        if self.input_fp_id_valid:
            self.keys.append('Work_ID')
            self.values.append(self.input_fp_id)
        if self.input_fa_id_valid:
            self.keys.append('Project_ID')
            self.values.append(self.input_fa_id)
            
        l=convert_key_value(self.keys,self.values)
        
        self.get_res_rank_condition()
        self.get_res_funding_condition()
        
        if self.input_res_rank_valid:
            l.append(self.res_rank_condition)
        if self.input_res_funding_valid:
            l.append(self.res_funding_condition)
            
        self.condition=convert_and_condition(l)
        
        self.UI_action()
        
    def insert_teach(self):
        pk=self.check_insert_primary_key([self.input_fp_id,self.input_fa_id,self.input_year,self.input_semester],self.input_fp_id_valid and self.input_fa_id_valid)
        if not pk:
            self.use_warning_message('警告','非法的主键！')
            return
        fk=self.check_insert_foreign_key([self.input_fp_id,self.input_fa_id],self.input_fp_id_valid and self.input_fa_id_valid)
        if not fk:
            self.use_warning_message('警告','非法的外键！')
            return
        self.values=[]
        valid=1
        if self.input_fp_id_valid:
            self.values.append(self.input_fp_id)
        else:
            self.values.append('None')
            valid=0
        if self.input_fa_id_valid:
            self.values.append(self.input_fa_id)
        else:
            self.values.append('None')
            valid=0
        if self.input_year_valid:
            self.values.append(self.input_year)
        else:
            self.values.append('None')
            valid=0
        if self.input_semester_valid:
            self.values.append(self.input_semester)
        else:
            self.values.append('None')
            valid=0
        if self.input_hour_valid:
            self.values.append(self.input_hour)
        else:
            self.values.append('None')
            valid=0
            
        if not valid:
            ret=self.use_question_message('信息缺失','有部分信息未填写或无效。确定仍然要插入吗？')
            if ret==QMessageBox.No:
                return
        
        if not (self.input_fa_id in self.check_course):
            self.check_course.append(self.input_fa_id)
        
        self.UI_action()
        
    def update_teach(self):
        db=self.db
        table=self.table
        condition=self.current_condition
        
        n,l=select(db,table,condition)
        
        pk=True
        for e in l:
            input_fp_id=self.input_fp_id if self.input_fp_id_valid_update else e[key_dict[table].index('Work_ID')]
            input_fa_id=self.input_fa_id if self.input_fa_id_valid_update else e[key_dict[table].index('Course_ID')]
            fp_id_valid=self.input_fp_id_valid_update or self.input_fp_id_valid
            fa_id_valid=self.input_fa_id_valid_update or self.input_fa_id_valid
            pk=pk and self.check_insert_primary_key([input_fp_id,input_fa_id,self.input_year,self.input_semester],fp_id_valid and fa_id_valid and self.input_year_valid and self.input_semester_valid)
        if (not pk) and (self.input_fp_id_valid_update and self.input_fa_id_valid_update and self.input_year_valid and self.input_semester_valid):
            self.use_warning_message('警告','存在非法的主键！')
            return
        self.keys=[]
        self.values=[]
        if self.input_fp_id_valid_update:
            self.keys.append('Work_ID')
            self.values.append(self.input_fp_id)
        if self.input_fa_id_valid_update:
            self.keys.append('Course_ID')
            self.values.append(self.input_fa_id)
        if self.input_year_valid_update:
            self.keys.append('Course_Year')
            self.values.append(self.input_year)
        if self.input_semester_valid_update:
            self.keys.append('Semester')
            self.values.append(self.input_semester)
        if self.input_hour_valid_update:
            self.keys.append('Responsible_Hour')
            self.values.append(self.input_hour)
            
        print(self.keys)
        print(self.values)
            
        db=self.db
        table=self.table
        condition=self.current_condition
        
        n,l=select(db,table,condition)
        
        for e in l:
            current_id=e[key_dict[table].index('Course_ID')]
            if not (current_id in self.check_course):
                self.check_course.append(current_id)
        
        current_id=self.input_fa_id
        if self.input_fa_id_valid_update and (not current_id in self.check_course):
            self.check_course.append(current_id)
        
        self.UI_action()
        
        self.operation='select'
        self.UI_action()
        
        self.operation='update'
        
    def select_teach(self):
        self.keys=[]
        self.values=[]
        if self.input_fp_id_valid:
            self.keys.append('Work_ID')
            self.values.append(self.input_fp_id)
        if self.input_fa_id_valid:
            self.keys.append('Course_ID')
            self.values.append(self.input_fa_id)
        if self.input_year_valid:
            self.keys.append('Course_Year')
            self.values.append(self.input_year)
            
        l=convert_key_value(self.keys,self.values)
        
        self.get_semester_condition()
        self.get_res_hour_condition()
        
        if self.input_semester_valid:
            l.append(self.semester_condition)
        if self.input_res_hour_valid:
            l.append(self.res_hour_condition)
            
        self.condition=convert_and_condition(l)
        
        self.UI_action()
        
    def delete_select_result(self):
        if not self.have_result:
            self.use_warning_message('操作失败','需要至少一个目标！')
        else:
            db=self.db
            table=self.table
            condition=self.current_condition
            
            n,l=select(db,table,condition)
            
            if table=='Project':
                for e in l:
                    current_id=e[key_dict[table].index('Project_ID')]
                    if current_id in self.check_project:
                        self.check_project.remove(current_id)
            elif table=='Course':
                for e in l:
                    current_id=e[key_dict[table].index('Course_ID')]
                    if current_id in self.check_course:
                        self.check_course.remove(current_id)
            elif table=='Undertake':
                for e in l:
                    current_id=e[key_dict[table].index('Project_ID')]
                    if not (current_id in self.check_project):
                        self.check_project.append(current_id)
            elif table=='Teach':
                for e in l:
                    current_id=e[key_dict[table].index('Course_ID')]
                    if not (current_id in self.check_course):
                        self.check_course.append(current_id)
            
            self.operation='delete'
            self.condition=self.current_condition
            self.UI_action()
            # 恢复到原界面并刷新结果
            self.operation='select'
            self.UI_action()
        
    def welcome_choose_target(self,text):
        if text>0:
            self.table=(list(key_dict.keys()))[text-1]
        else:
            self.table=''
        
    def enter_insert(self):
        if self.table=='':
            self.use_warning_message('无对象','请在下拉框中选择操作对象！')
        else:
            self.operation='insert'
            self.remove_welcome_layout()
            if (not self.table in foreign_table_dict.keys()):
                self.use_simple_insert_layout()
            else:
                self.use_foreign_insert_layout()
        
    def enter_select(self):
        if self.table=='':
            self.use_warning_message('无对象','请在下拉框中选择操作对象！')
        else:
            self.operation='select'
            self.remove_welcome_layout()
            if (not self.table in foreign_table_dict.keys()):
                self.use_simple_select_layout()
            else:
                self.use_foreign_select_layout()
                
    # 检查插入时给出的主键是否合法
    def check_insert_primary_key(self,values,valid):
        # valid应当是所有主键的valid的与规约
        if not valid:
            return False
        # values是所有主键的列表
        db=self.db
        table=self.table
        keys=primary_key_dict[table]
        condition_list=convert_key_value(keys,values)
        condition=convert_and_condition(condition_list)
        n,l=select(db,table,condition)
        if n>0:
            return False
        return True
    
    # 检查输入时给出的外键是否合法
    def check_insert_foreign_key(self,values,valid):
        # 利用了已知信息：每个外键都是一个不同的表的唯一主键
        if not valid:
            return False
        db=self.db
        table=self.table
        
        foreign_tables=foreign_table_dict[table]
        eligible=True
        availibility=[]
        foreign_info=[]
        for e in foreign_tables:
            pk_list=primary_key_dict[e]
            select_keys=[]
            select_values=[]
            for pk in pk_list:
                pk_value=values[foreign_tables.index(e)]
                select_keys.append(pk)
                select_values.append(pk_value)
            condition_list=convert_key_value(select_keys,select_values)
            condition=convert_and_condition(condition_list)
            n,l=select(db,e,condition)
            availibility.append((n>0))
            # 这里应当一次只新增一个元素，因为根据题目的描述，外键都是所在的表的主键
            foreign_info.append(l)
            if n==0:
                eligible=False
        # print(availibility)
        # print(foreign_info)
        return eligible
    
    def swap_accept_publish_date(self):
        if self.accept_publish_date_box.isChecked():
            self.max_publish_date_edit_s.setEnabled(True)
            self.min_publish_date_edit_s.setEnabled(True)
            self.input_max_publish_date_valid=1
            self.input_min_publish_date_valid=1
            self.input_publish_date_valid=1
        else:
            self.max_publish_date_edit_s.setEnabled(False)
            self.min_publish_date_edit_s.setEnabled(False)
            self.input_max_publish_date_valid=0
            self.input_min_publish_date_valid=0
            self.input_publish_date_valid=0
    
    def swap_accept_start_date(self):
        if self.accept_start_date_box.isChecked():
            self.max_start_date_edit_s.setEnabled(True)
            self.min_start_date_edit_s.setEnabled(True)
            self.input_max_start_date_valid=1
            self.input_min_start_date_valid=1
            self.input_start_date_valid=1
        else:
            self.max_start_date_edit_s.setEnabled(False)
            self.min_start_date_edit_s.setEnabled(False)
            self.input_max_start_date_valid=0
            self.input_min_start_date_valid=0
            self.input_start_date_valid=0
            
    def swap_accept_end_date(self):
        if self.accept_end_date_box.isChecked():
            self.max_end_date_edit_s.setEnabled(True)
            self.min_end_date_edit_s.setEnabled(True)
            self.input_max_end_date_valid=1
            self.input_min_end_date_valid=1
            self.input_end_date_valid=1
        else:
            self.max_end_date_edit_s.setEnabled(False)
            self.min_end_date_edit_s.setEnabled(False)
            self.input_max_end_date_valid=0
            self.input_min_end_date_valid=0
            self.input_end_date_valid=0
            
    def swap_accept_author_rank(self):
        if self.accept_author_rank_box.isChecked():
            self.max_seq_edit_s.setEnabled(True)
            self.min_seq_edit_s.setEnabled(True)
            self.input_max_author_rank_valid=1
            self.input_min_author_rank_valid=1
            self.input_author_rank_valid=1
        else:
            self.max_seq_edit_s.setEnabled(False)
            self.min_seq_edit_s.setEnabled(False)
            self.input_max_author_rank_valid=0
            self.input_min_author_rank_valid=0
            self.input_author_rank_valid=0
            
    def swap_accept_res_rank(self):
        if self.accept_res_rank_box.isChecked():
            self.max_seq_edit_s.setEnabled(True)
            self.min_seq_edit_s.setEnabled(True)
            self.input_max_res_rank_valid=1
            self.input_min_res_rank_valid=1
            self.input_res_rank_valid=1
        else:
            self.max_seq_edit_s.setEnabled(False)
            self.min_seq_edit_s.setEnabled(False)
            self.input_max_res_rank_valid=0
            self.input_min_res_rank_valid=0
            self.input_res_rank_valid=0
            
    def swap_accept_res_funding(self):
        if self.accept_res_funding_box.isChecked():
            self.max_res_funding_edit_s.setEnabled(True)
            self.min_res_funding_edit_s.setEnabled(True)
            self.input_max_res_funding_valid=1
            self.input_min_res_funding_valid=1
            self.input_res_funding_valid=1
        else:
            self.max_res_funding_edit_s.setEnabled(False)
            self.min_res_funding_edit_s.setEnabled(False)
            self.input_max_res_funding_valid=0
            self.input_min_res_funding_valid=0
            self.input_res_funding_valid=0
            
    def swap_accept_res_hour(self):
        if self.accept_res_hour_box.isChecked():
            self.max_res_hour_edit_s.setEnabled(True)
            self.min_res_hour_edit_s.setEnabled(True)
            self.input_max_res_hour_valid=1
            self.input_min_res_hour_valid=1
            self.input_res_hour_valid=1
        else:
            self.max_res_hour_edit_s.setEnabled(False)
            self.min_res_hour_edit_s.setEnabled(False)
            self.input_max_res_hour_valid=0
            self.input_min_res_hour_valid=0
            self.input_res_hour_valid=0
    
    def back2welcome_simple_insert(self):
        self.remove_simple_insert_layout()
        self.use_welcome_layout()
        
    def back2welcome_foreign_insert(self):
        self.remove_foreign_insert_layout()
        self.use_welcome_layout()
    
    def back2welcome_simple_select(self):
        self.remove_simple_select_layout()
        self.use_welcome_layout()
        
    def back2welcome_foreign_select(self):
        self.remove_foreign_select_layout()
        self.use_welcome_layout()
        
    def use_simple_insert_layout(self):
        self.action_button=QPushButton('插入',self)
        self.action_button.setVisible(True)
        
        self.back2welcome_button=QPushButton('返回',self)
        self.back2welcome_button.clicked.connect(self.back2welcome_simple_insert)
        self.back2welcome_button.setVisible(True)
        
        self.action_button.setGeometry(550,1400,150,40)
        self.back2welcome_button.setGeometry(1300,1400,150,40)
        
        if self.table=='Professor':
            self.id_edit=QLineEdit(self)
            self.id_edit.setText('请输入工号')
            self.id_edit.textChanged.connect(self.get_input_ID)
            self.id_edit.setVisible(True)
            self.input_id=''
            self.input_id_valid=0
            
            self.name_edit=QLineEdit(self)
            self.name_edit.setText('请输入姓名')
            self.name_edit.textChanged.connect(self.get_input_name)
            self.name_edit.setVisible(True)
            self.input_name=''
            self.input_name_valid=0
            
            self.fradio=QRadioButton('女',self)
            self.mradio=QRadioButton('男',self)
            self.fradio.setChecked(True)
            self.fradio.toggled.connect(self.swap_gender)
            self.mradio.toggled.connect(self.swap_gender)
            self.fradio.setVisible(True)
            self.mradio.setVisible(True)
            self.input_gender=2
            self.input_gender_valid=1
            
            self.title_box=QComboBox(self)
            self.title_box.addItem('职称')
            self.title_box.addItems(titles)
            self.title_box.currentIndexChanged.connect(self.get_input_title)
            self.title_box.setVisible(True)
            self.input_title=0
            self.input_title_valid=0
            
            self.action_button.clicked.connect(self.insert_professor)
            
            self.id_edit.setGeometry(200,200,200,40)
            self.name_edit.setGeometry(500,200,200,40)
            self.fradio.setGeometry(800,200,100,40)
            self.mradio.setGeometry(950,200,100,40)
            self.title_box.setGeometry(1100,200,200,40)
            
        elif self.table=='Essai':
            self.id_edit=QLineEdit(self)
            self.id_edit.setText('请输入编号')
            self.id_edit.textChanged.connect(self.get_input_ID_number)
            self.id_edit.setVisible(True)
            self.input_id_number=0
            self.input_id_valid=0
            
            self.name_edit=QLineEdit(self)
            self.name_edit.setText('请输入论文标题')
            self.name_edit.textChanged.connect(self.get_input_name)
            self.name_edit.setVisible(True)
            self.input_name=''
            self.input_name_valid=0
            
            self.publish_source_edit=QLineEdit(self)
            self.publish_source_edit.setText('请输入发表源')
            self.publish_source_edit.textChanged.connect(self.get_input_source)
            self.publish_source_edit.setVisible(True)
            self.input_source=''
            self.input_source_valid=0
            
            self.publish_date_edit=QDateEdit(self)
            self.publish_date_edit.setMaximumDate(QDate.currentDate())
            self.publish_date_edit.setDate(QDate.currentDate())
            self.publish_date_edit.dateChanged.connect(self.get_publish_date)
            self.publish_date_edit.setVisible(True)
            year=str(QDate.currentDate().year())
            month=str(QDate.currentDate().month())
            day=str(QDate.currentDate().day())
            self.input_publish_date=year+'/'+month+'/'+day
            self.input_publish_date_valid=1
            
            self.type_box=QComboBox(self)
            self.type_box.addItem('论文类型')
            self.type_box.addItems(essai_type)
            self.type_box.currentIndexChanged.connect(self.get_input_type)
            self.type_box.setVisible(True)
            self.input_type=0
            self.input_type_valid=0
            
            self.rank_box=QComboBox(self)
            self.rank_box.addItem('论文级别')
            self.rank_box.addItems(essai_rank)
            self.rank_box.currentIndexChanged.connect(self.get_input_rank)
            self.rank_box.setVisible(True)
            self.input_rank=0
            self.input_rank_valid=0
            
            self.action_button.clicked.connect(self.insert_essai)
            
            self.id_edit.setGeometry(200,200,200,40)
            self.name_edit.setGeometry(500,200,500,40)
            self.publish_source_edit.setGeometry(200,300,1000,40)
            self.publish_date_edit.setGeometry(200,400,300,40)
            self.type_box.setGeometry(650,400,200,40)
            self.rank_box.setGeometry(1000,400,200,40)
            
        elif self.table=='Project':
            self.id_edit=QLineEdit(self)
            self.id_edit.setText('请输入项目号')
            self.id_edit.textChanged.connect(self.get_input_ID)
            self.id_edit.setVisible(True)
            self.input_id=''
            self.input_id_valid=0
            
            self.name_edit=QLineEdit(self)
            self.name_edit.setText('请输入项目名称')
            self.name_edit.textChanged.connect(self.get_input_name)
            self.name_edit.setVisible(True)
            self.input_name=''
            self.input_name_valid=0
            
            self.source_edit=QLineEdit(self)
            self.source_edit.setText('请输入项目来源')
            self.source_edit.textChanged.connect(self.get_input_source)
            self.source_edit.setVisible(True)
            self.input_source=''
            self.input_source_valid=0
            
            self.type_box=QComboBox(self)
            self.type_box.addItem('项目类型')
            self.type_box.addItems(project_type)
            self.type_box.currentIndexChanged.connect(self.get_input_type)
            self.type_box.setVisible(True)
            self.input_type=0
            self.input_type_valid=0
            
            self.total_funding_edit=QLineEdit(self)
            self.total_funding_edit.setText('请输入总经费')
            self.total_funding_edit.setVisible(True)
            self.total_funding_edit.textChanged.connect(self.get_input_funding)
            self.input_funding=0.0
            self.input_funding_valid=0
            
            self.start_date_edit=QDateEdit(self)
            self.start_date_edit.setMaximumDate(QDate.currentDate())
            self.start_date_edit.setDate(QDate.currentDate())
            self.start_date_edit.dateChanged.connect(self.get_start_date)
            self.start_date_edit.setVisible(True)
            year=str(QDate.currentDate().year())
            month=str(QDate.currentDate().month())
            day=str(QDate.currentDate().day())
            self.input_start_date=year+'/'+month+'/'+day
            self.input_start_date_valid=1
            
            self.end_date_edit=QDateEdit(self)
            self.end_date_edit.setDate(QDate.currentDate())
            self.end_date_edit.dateChanged.connect(self.get_end_date)
            self.end_date_edit.setVisible(True)
            year=str(QDate.currentDate().year())
            month=str(QDate.currentDate().month())
            day=str(QDate.currentDate().day())
            self.input_end_date=year+'/'+month+'/'+day
            self.input_end_date_valid=1
            
            self.action_button.clicked.connect(self.insert_project)
            
            self.id_edit.setGeometry(200,200,200,40)
            self.name_edit.setGeometry(500,200,200,40)
            self.source_edit.setGeometry(200,300,1000,40)
            self.type_box.setGeometry(200,400,200,40)
            self.total_funding_edit.setGeometry(500,400,200,40)
            self.start_date_edit.setGeometry(800,400,200,40)
            self.end_date_edit.setGeometry(1100,400,200,40)
            
        elif self.table=='Course':
            self.id_edit=QLineEdit(self)
            self.id_edit.setText('请输入编号')
            self.id_edit.textChanged.connect(self.get_input_ID)
            self.id_edit.setVisible(True)
            self.input_id=''
            self.input_id_valid=0
            
            self.name_edit=QLineEdit(self)
            self.name_edit.setText('请输入课程名')
            self.name_edit.textChanged.connect(self.get_input_name)
            self.name_edit.setVisible(True)
            self.input_name=''
            self.input_name_valid=0
            
            self.hour_edit=QLineEdit(self)
            self.hour_edit.setText('请输入课时数')
            self.hour_edit.textChanged.connect(self.get_input_hour)
            self.hour_edit.setVisible(True)
            self.input_hour=0
            self.input_hour_valid=0
            
            self.type_sradio=QRadioButton('本科生课程',self)
            self.type_bradio=QRadioButton('研究生课程',self)
            self.type_sradio.setChecked(True)
            self.type_sradio.toggled.connect(self.swap_course_type)
            self.type_bradio.toggled.connect(self.swap_course_type)
            self.type_sradio.setVisible(True)
            self.type_bradio.setVisible(True)
            self.input_type=1
            self.input_type_valid=1
            
            self.action_button.clicked.connect(self.insert_course)
            
            self.id_edit.setGeometry(200,200,200,40)
            self.name_edit.setGeometry(500,200,200,40)
            self.hour_edit.setGeometry(800,200,150,40)
            self.type_sradio.setGeometry(1050,200,200,40)
            self.type_bradio.setGeometry(1250,200,1200,40)
        
    def remove_simple_insert_layout(self):
        if self.table=='Professor':
            self.id_edit.setVisible(False)
            self.name_edit.setVisible(False)
            self.fradio.setVisible(False)
            self.mradio.setVisible(False)
            self.title_box.setVisible(False)
        elif self.table=='Essai':
            self.id_edit.setVisible(False)
            self.name_edit.setVisible(False)
            self.publish_source_edit.setVisible(False)
            self.publish_date_edit.setVisible(False)
            self.type_box.setVisible(False)
            self.rank_box.setVisible(False)
        elif self.table=='Project':
            self.id_edit.setVisible(False)
            self.name_edit.setVisible(False)
            self.source_edit.setVisible(False)
            self.type_box.setVisible(False)
            self.total_funding_edit.setVisible(False)
            self.start_date_edit.setVisible(False)
            self.end_date_edit.setVisible(False)
        elif self.table=='Course':
            self.id_edit.setVisible(False)
            self.name_edit.setVisible(False)
            self.hour_edit.setVisible(False)
            self.type_sradio.setVisible(False)
            self.type_bradio.setVisible(False)
        
        self.action_button.setVisible(False)
        self.back2welcome_button.setVisible(False)
        
    def use_foreign_insert_layout(self):
        self.fp_output_table=QTableWidget(self)
        self.fp_output_table.setVisible(False)
        
        self.fa_output_table=QTableWidget(self)
        self.fa_output_table.setVisible(False)
        
        self.foreign_table_status=0 # 无，仅有职工外键，仅有其余外键，两个外键均有
        
        self.action_button=QPushButton('插入',self)
        self.action_button.setVisible(True)
        
        self.back2welcome_button=QPushButton('返回',self)
        self.back2welcome_button.clicked.connect(self.back2welcome_foreign_insert)
        self.back2welcome_button.setVisible(True)
        
        self.action_button.setGeometry(550,1400,150,40)
        self.back2welcome_button.setGeometry(1300,1400,150,40)
        
        if self.table=='Publish':
            self.fp_table='Professor'
            self.fa_table='Essai'
            
            self.id_edit_p=QLineEdit(self)
            self.id_edit_p.setText('请输入工号')
            self.id_edit_p.textChanged.connect(self.get_input_fp_ID)
            self.id_edit_p.setVisible(True)
            self.input_fp_id=''
            self.input_fp_id_valid=0
            
            self.id_edit_f=QLineEdit(self)
            self.id_edit_f.setText('请输入编号')
            self.id_edit_f.textChanged.connect(self.get_input_fa_ID_number)
            self.id_edit_f.setVisible(True)
            self.input_fa_id_number=0
            self.input_fa_id_valid=0
            
            self.seq_edit=QLineEdit(self)
            self.seq_edit.setText('请输入作者排名')
            self.seq_edit.textChanged.connect(self.get_author_rank)
            self.seq_edit.setVisible(True)
            self.input_author_rank=''
            self.input_author_rank_valid=0
            
            self.comm_author_box=QCheckBox('是否为通讯作者',self)
            self.comm_author_box.stateChanged.connect(self.swap_comm_author)
            self.comm_author_box.setVisible(True)
            self.input_is_comm_author=0
            self.input_is_comm_author_valid=1
            
            self.fp_box=QCheckBox('显示教授信息',self)
            self.fp_box.stateChanged.connect(self.change_fp_status_insert)
            self.fp_box.setVisible(True)
            
            self.fa_box=QCheckBox('显示论文信息',self)
            self.fa_box.stateChanged.connect(self.change_fa_status_insert)
            self.fa_box.setVisible(True)
            
            self.fp_box.setGeometry(300,400,200,40)
            self.fa_box.setGeometry(600,400,200,40)
            
            self.action_button.clicked.connect(self.insert_publish)
            
            self.id_edit_p.setGeometry(200,200,200,40)
            self.id_edit_f.setGeometry(500,200,200,40)
            self.seq_edit.setGeometry(800,200,200,40)
            self.comm_author_box.setGeometry(1100,200,200,40)
        elif self.table=='Undertake':
            self.fp_table='Professor'
            self.fa_table='Project'
            
            self.id_edit_p=QLineEdit(self)
            self.id_edit_p.setText('请输入工号')
            self.id_edit_p.textChanged.connect(self.get_input_fp_ID)
            self.id_edit_p.setVisible(True)
            self.input_fp_id=''
            self.input_fp_id_valid=0
            
            self.id_edit_f=QLineEdit(self)
            self.id_edit_f.setText('请输入项目号')
            self.id_edit_f.textChanged.connect(self.get_input_fa_ID)
            self.id_edit_f.setVisible(True)
            self.input_fa_id=''
            self.input_fa_id_valid=0
            
            self.seq_edit=QLineEdit(self)
            self.seq_edit.setText('请输入承担排名')
            self.seq_edit.textChanged.connect(self.get_res_rank)
            self.seq_edit.setVisible(True)
            self.input_res_rank=0
            self.input_res_rank_valid=0
            
            self.res_funding_edit=QLineEdit(self)
            self.res_funding_edit.setText('请输入承担经费')
            self.res_funding_edit.textChanged.connect(self.get_input_funding)
            self.res_funding_edit.setVisible(True)
            self.input_funding=0.0
            self.input_funding_valid=0
            
            self.fp_box=QCheckBox('显示教授信息',self)
            self.fp_box.stateChanged.connect(self.change_fp_status_insert)
            self.fp_box.setVisible(True)
            
            self.fa_box=QCheckBox('显示项目信息',self)
            self.fa_box.stateChanged.connect(self.change_fa_status_insert)
            self.fa_box.setVisible(True)
                
            self.fp_box.setGeometry(300,400,200,40)
            self.fa_box.setGeometry(600,400,200,40)
            
            self.action_button.clicked.connect(self.insert_undertake)
            
            self.id_edit_p.setGeometry(200,200,200,40)
            self.id_edit_f.setGeometry(500,200,200,40)
            self.seq_edit.setGeometry(800,200,200,40)
            self.res_funding_edit.setGeometry(1100,200,200,40)
        elif self.table=='Teach':
            self.fp_table='Professor'
            self.fa_table='Course'
            
            self.id_edit_p=QLineEdit(self)
            self.id_edit_p.setText('请输入工号')
            self.id_edit_p.textChanged.connect(self.get_input_fp_ID)
            self.id_edit_p.setVisible(True)
            self.input_fp_id=''
            self.input_fp_id_valid=0
            
            self.id_edit_f=QLineEdit(self)
            self.id_edit_f.setText('请输入编号')
            self.id_edit_f.textChanged.connect(self.get_input_fa_ID)
            self.id_edit_f.setVisible(True)
            self.input_fa_id=''
            self.input_fa_id_valid=0
            
            self.course_year_box=QComboBox(self)
            self.course_year_box.addItems([str(i) for i in self.year_list])
            self.course_year_box.currentIndexChanged.connect(self.get_input_year)
            self.course_year_box.setVisible(True)
            self.input_year=self.year_list[0]
            self.input_year_valid=1
            
            # 可以增加一个根据当前日期自动确定当前学期的功能
            self.semester_box=QComboBox(self)
            self.semester_box.addItems(semesters)
            self.semester_box.currentIndexChanged.connect(self.get_input_semester)
            self.semester_box.setVisible(True)
            self.input_semester=1
            self.input_semester_valid=1
            
            self.res_hour_edit=QLineEdit(self)
            self.res_hour_edit.setText('请输入负责课时数')
            self.res_hour_edit.textChanged.connect(self.get_input_hour)
            self.res_hour_edit.setVisible(True)
            self.input_hour=0
            self.input_hour_valid=0
            
            self.fp_box=QCheckBox('显示教授信息',self)
            self.fp_box.stateChanged.connect(self.change_fp_status_insert)
            self.fp_box.setVisible(True)
            
            self.fa_box=QCheckBox('显示课程信息',self)
            self.fa_box.stateChanged.connect(self.change_fa_status_insert)
            self.fa_box.setVisible(True)
                
            self.fp_box.setGeometry(300,400,200,40)
            self.fa_box.setGeometry(600,400,200,40)
            
            self.action_button.clicked.connect(self.insert_teach)
                
            self.id_edit_p.setGeometry(200,200,200,40)
            self.id_edit_f.setGeometry(500,200,200,40)
            self.course_year_box.setGeometry(800,200,150,40)
            self.semester_box.setGeometry(1050,200,200,40)
            self.res_hour_edit.setGeometry(1350,200,250,40)
        
    def remove_foreign_insert_layout(self):
        if self.table=='Publish':
            self.id_edit_p.setVisible(False)
            self.id_edit_f.setVisible(False)
            self.seq_edit.setVisible(False)
            self.comm_author_box.setVisible(False)
        elif self.table=='Undertake':
            self.id_edit_p.setVisible(False)
            self.id_edit_f.setVisible(False)
            self.seq_edit.setVisible(False)
            self.res_funding_edit.setVisible(False)
        elif self.table=='Teach':
            self.id_edit_p.setVisible(False)
            self.id_edit_f.setVisible(False)
            self.course_year_box.setVisible(False)
            self.semester_box.setVisible(False)
            self.res_hour_edit.setVisible(False)
        
        self.fp_box.setVisible(False)
        self.fa_box.setVisible(False)
        self.fp_output_table.setVisible(False)
        self.fa_output_table.setVisible(False)
        self.action_button.setVisible(False)
        self.back2welcome_button.setVisible(False)
        
    def use_simple_select_layout(self):
        self.output_table=QTableWidget(self)
        self.output_table.setVisible(True)
    
        self.action_button=QPushButton('查找',self)
        self.action_button.setVisible(True)
        
        self.delete_button=QPushButton('一键删除',self)
        self.delete_button.clicked.connect(self.delete_select_result)
        self.delete_button.setVisible(True)
        
        self.update_button=QPushButton('一键更新',self)
        self.update_button.clicked.connect(self.change2simple_update)
        self.update_button.setVisible(True)
        
        self.back2welcome_button=QPushButton('返回',self)
        self.back2welcome_button.clicked.connect(self.back2welcome_simple_select)
        self.back2welcome_button.setVisible(True)
        
        self.output_table.setGeometry(300,500,1400,800)
        self.action_button.setGeometry(550,1400,150,40)
        self.delete_button.setGeometry(800,1400,150,40)
        self.update_button.setGeometry(1050,1400,150,40)
        self.back2welcome_button.setGeometry(1300,1400,150,40)
        
        if self.table=='Professor':
            self.id_edit_s=QLineEdit(self)
            self.id_edit_s.setText('请输入工号')
            self.id_edit_s.textChanged.connect(self.get_input_ID)
            self.id_edit_s.setVisible(True)
            self.input_id=''
            self.input_id_valid=0
            
            self.name_edit_s=QLineEdit(self)
            self.name_edit_s.setText('请输入姓名')
            self.name_edit_s.textChanged.connect(self.get_input_name)
            self.name_edit_s.setVisible(True)
            self.input_name=''
            self.input_name_valid=0
            
            self.fbox_s=QCheckBox('女',self)
            self.mbox_s=QCheckBox('男',self)
            self.fbox_s.setVisible(True)
            self.mbox_s.setVisible(True)
            self.fbox_s.stateChanged.connect(self.get_gender_choice)
            self.mbox_s.stateChanged.connect(self.get_gender_choice)
            self.gender_choice=[]
            self.gender_condition=''
            self.input_gender_valid=0
            
            # 用列表保存所有可能的职称
            self.title_box_s=[]
            for e in titles:
                self.title_box_s.append(QCheckBox(e,self))
                idx=titles.index(e)
                self.title_box_s[idx].stateChanged.connect(self.get_title_choice)
                self.title_box_s[idx].setVisible(True)
            self.title_choice=''
            self.title_condition=''
            self.input_title_valid=0
            
            self.action_button.clicked.connect(self.select_professor)
            
            self.output_button=QPushButton('全部导出',self)
            self.output_button.clicked.connect(self.output_all)
            self.output_button.setVisible(True)
            self.action_button.setGeometry(450,1400,150,40)
            self.delete_button.setGeometry(700,1400,150,40)
            self.update_button.setGeometry(950,1400,150,40)
            self.back2welcome_button.setGeometry(1200,1400,150,40)
            self.output_button.setGeometry(1450,1400,150,40)
            
            self.year_f_s=QLineEdit(self)
            self.year_f_s.setText('请输入导出起始年份')
            self.year_f_s.textChanged.connect(self.get_input_year_f)
            self.year_f_s.setVisible(True)
            self.year_f=self.min_year
            self.year_f_s.setGeometry(1050,200,250,40)
            
            self.year_t_s=QLineEdit(self)
            self.year_t_s.setText('请输入导出起始年份')
            self.year_t_s.textChanged.connect(self.get_input_year_t)
            self.year_t_s.setVisible(True)
            self.year_t=self.max_year
            self.year_t_s.setGeometry(1400,200,250,40)
            
            self.id_edit_s.setGeometry(200,200,200,40)
            self.name_edit_s.setGeometry(500,200,200,40)
            self.fbox_s.setGeometry(800,200,100,40)
            self.mbox_s.setGeometry(950,200,100,40)
            for e in self.title_box_s:
                idx=self.title_box_s.index(e)
                if idx<6:
                    e.setGeometry(idx*250+200,300,200,40)
                else:
                    e.setGeometry((idx-6)*250+200,400,200,40)
            
        elif self.table=='Essai':
            self.id_edit_s=QLineEdit(self)
            self.id_edit_s.setText('请输入编号')
            self.id_edit_s.textChanged.connect(self.get_input_ID_number)
            self.id_edit_s.setVisible(True)
            self.input_id_number=0
            self.input_id_valid=0
            
            self.name_edit_s=QLineEdit(self)
            self.name_edit_s.setText('请输入论文标题')
            self.name_edit_s.textChanged.connect(self.get_input_name)
            self.name_edit_s.setVisible(True)
            self.input_name=''
            self.input_name_valid=0
            
            self.publish_source_edit_s=QLineEdit(self)
            self.publish_source_edit_s.setText('请输入发表源')
            self.publish_source_edit_s.textChanged.connect(self.get_input_source)
            self.publish_source_edit_s.setVisible(True)
            self.input_source=''
            self.input_source_valid=0
            
            self.max_publish_date_edit_s=QDateEdit(self)
            self.max_publish_date_edit_s.setDate(QDate.currentDate())
            self.max_publish_date_edit_s.dateChanged.connect(self.get_max_publish_date)
            self.max_publish_date_edit_s.setVisible(True)
            year=str(QDate.currentDate().year())
            month=str(QDate.currentDate().month())
            day=str(QDate.currentDate().day())
            self.input_max_publish_date=year+'/'+month+'/'+day
            self.input_max_publish_date_valid=0
            
            self.min_publish_date_edit_s=QDateEdit(self)
            self.min_publish_date_edit_s.setDate(QDate.currentDate())
            self.min_publish_date_edit_s.dateChanged.connect(self.get_min_publish_date)
            self.min_publish_date_edit_s.setVisible(True)
            year=str(QDate.currentDate().year())
            month=str(QDate.currentDate().month())
            day=str(QDate.currentDate().day())
            self.input_min_publish_date=year+'/'+month+'/'+day
            self.input_min_publish_date_valid=0
            
            self.publish_date_condition=''
            self.input_publish_date_valid=0
            self.max_publish_date_edit_s.setEnabled(False)
            self.min_publish_date_edit_s.setEnabled(False)
            
            # 分别控制是否接受起止日期的控件
            self.accept_publish_date_box=QCheckBox('检测发表日期',self)
            self.accept_publish_date_box.stateChanged.connect(self.swap_accept_publish_date)
            self.accept_publish_date_box.setVisible(True)
            
            # 用列表保存所有可能的类型
            self.type_box_s=[]
            for e in essai_type:
                self.type_box_s.append(QCheckBox(e,self))
                idx=essai_type.index(e)
                self.type_box_s[idx].stateChanged.connect(self.get_essai_type_choice)
                self.type_box_s[idx].setVisible(True)
            self.essai_type_choice=''
            self.essai_type_condition=''
            self.input_type_valid=0
            
            # 用列表保存所有可能的级别
            self.rank_box_s=[]
            for e in essai_rank:
                self.rank_box_s.append(QCheckBox(e,self))
                idx=essai_rank.index(e)
                self.rank_box_s[idx].stateChanged.connect(self.get_essai_rank_choice)
                self.rank_box_s[idx].setVisible(True)
            self.essai_rank_choice=''
            self.essai_rank_condition=''
            self.input_rank_valid=0
            
            self.action_button.clicked.connect(self.select_essai)
            
            self.id_edit_s.setGeometry(200,200,200,40)
            self.name_edit_s.setGeometry(450,200,500,40)
            self.publish_source_edit_s.setGeometry(1000,200,800,40)
            self.accept_publish_date_box.setGeometry(200,300,200,40)
            self.max_publish_date_edit_s.setGeometry(500,300,200,40)
            self.min_publish_date_edit_s.setGeometry(800,300,200,40)
            for e in self.type_box_s:
                idx=self.type_box_s.index(e)
                e.setGeometry(idx*200+200,400,200,40)
            for e in self.rank_box_s:
                idx=self.rank_box_s.index(e)
                e.setGeometry(idx*200+1000,400,200,40)
            
        elif self.table=='Project':
            self.id_edit_s=QLineEdit(self)
            self.id_edit_s.setText('请输入项目号')
            self.id_edit_s.textChanged.connect(self.get_input_ID)
            self.id_edit_s.setVisible(True)
            self.input_id=''
            self.input_id_valid=0
            
            self.name_edit_s=QLineEdit(self)
            self.name_edit_s.setText('请输入项目名称')
            self.name_edit_s.textChanged.connect(self.get_input_name)
            self.name_edit_s.setVisible(True)
            self.input_name=''
            self.input_name_valid=0
            
            self.source_edit_s=QLineEdit(self)
            self.source_edit_s.setText('请输入项目来源')
            self.source_edit_s.textChanged.connect(self.get_input_source)
            self.source_edit_s.setVisible(True)
            self.input_source=''
            self.input_source_valid=0
            
            # 用列表保存所有可能的类型
            self.type_box_s=[]
            for e in project_type:
                self.type_box_s.append(QCheckBox(e,self))
                idx=project_type.index(e)
                self.type_box_s[idx].stateChanged.connect(self.get_project_type_choice)
                self.type_box_s[idx].setVisible(True)
            self.project_type_choice=''
            self.project_type_condition=''
            self.input_type_valid=0
            
            # 通过让用户输入范围进行查找
            self.max_funding_edit_s=QLineEdit(self)
            self.max_funding_edit_s.setText('请输入经费上界')
            self.max_funding_edit_s.textChanged.connect(self.get_input_max_funding)
            self.max_funding_edit_s.setVisible(True)
            self.input_max_funding=0
            self.input_max_funding_valid=0
            
            self.min_funding_edit_s=QLineEdit(self)
            self.min_funding_edit_s.setText('请输入经费下界')
            self.min_funding_edit_s.textChanged.connect(self.get_input_min_funding)
            self.min_funding_edit_s.setVisible(True)
            self.input_min_funding=0
            self.input_min_funding_valid=0
            
            self.funding_condition=''
            self.input_funding_valid=0
            
            self.max_start_date_edit_s=QDateEdit(self)
            self.max_start_date_edit_s.setMaximumDate(QDate.currentDate())
            self.max_start_date_edit_s.setDate(QDate.currentDate())
            self.max_start_date_edit_s.dateChanged.connect(self.get_max_start_date)
            self.max_start_date_edit_s.setVisible(True)
            year=str(QDate.currentDate().year())
            month=str(QDate.currentDate().month())
            day=str(QDate.currentDate().day())
            self.input_max_start_date=year+'/'+month+'/'+day
            self.input_max_start_date_valid=0
            
            self.min_start_date_edit_s=QDateEdit(self)
            self.min_start_date_edit_s.setMaximumDate(QDate.currentDate())
            self.min_start_date_edit_s.setDate(QDate.currentDate())
            self.min_start_date_edit_s.dateChanged.connect(self.get_min_start_date)
            self.min_start_date_edit_s.setVisible(True)
            year=str(QDate.currentDate().year())
            month=str(QDate.currentDate().month())
            day=str(QDate.currentDate().day())
            self.input_min_start_date=year+'/'+month+'/'+day
            self.input_min_start_date_valid=0
            
            self.start_date_condition=''
            self.input_start_date_valid=0
            self.max_start_date_edit_s.setEnabled(False)
            self.min_start_date_edit_s.setEnabled(False)
            
            self.max_end_date_edit_s=QDateEdit(self)
            self.max_end_date_edit_s.setDate(QDate.currentDate())
            self.max_end_date_edit_s.dateChanged.connect(self.get_max_end_date)
            self.max_end_date_edit_s.setVisible(True)
            year=str(QDate.currentDate().year())
            month=str(QDate.currentDate().month())
            day=str(QDate.currentDate().day())
            self.input_max_end_date=year+'/'+month+'/'+day
            self.input_max_end_date_valid=0
            
            self.min_end_date_edit_s=QDateEdit(self)
            self.min_end_date_edit_s.setDate(QDate.currentDate())
            self.min_end_date_edit_s.dateChanged.connect(self.get_min_end_date)
            self.min_end_date_edit_s.setVisible(True)
            year=str(QDate.currentDate().year())
            month=str(QDate.currentDate().month())
            day=str(QDate.currentDate().day())
            self.input_min_end_date=year+'/'+month+'/'+day
            self.input_min_end_date_valid=0
            
            self.end_date_condition=''
            self.input_end_date_valid=0
            self.max_end_date_edit_s.setEnabled(False)
            self.min_end_date_edit_s.setEnabled(False)
            
            # 分别控制是否接受起止日期的控件
            self.accept_start_date_box=QCheckBox('检测开始日期',self)
            self.accept_end_date_box=QCheckBox('检测结束日期',self)
            self.accept_start_date_box.stateChanged.connect(self.swap_accept_start_date)
            self.accept_end_date_box.stateChanged.connect(self.swap_accept_end_date)
            self.accept_start_date_box.setVisible(True)
            self.accept_end_date_box.setVisible(True)
            
            self.action_button.clicked.connect(self.select_project)
            
            self.id_edit_s.setGeometry(200,200,200,40)
            self.name_edit_s.setGeometry(500,200,200,40)
            self.source_edit_s.setGeometry(800,200,800,40)
            for e in self.type_box_s:
                idx=self.type_box_s.index(e)
                e.setGeometry(idx*250+200,300,200,40)
            self.max_funding_edit_s.setGeometry(200,400,200,40)
            self.min_funding_edit_s.setGeometry(450,400,200,40)
            self.accept_start_date_box.setGeometry(700,400,200,40)
            self.accept_end_date_box.setGeometry(950,400,200,40)
            self.max_start_date_edit_s.setGeometry(1200,400,150,40)
            self.min_start_date_edit_s.setGeometry(1400,400,150,40)
            self.max_end_date_edit_s.setGeometry(1600,400,150,40)
            self.min_end_date_edit_s.setGeometry(1800,400,150,40)
            
        elif self.table=='Course':
            self.id_edit_s=QLineEdit(self)
            self.id_edit_s.setText('请输入编号')
            self.id_edit_s.textChanged.connect(self.get_input_ID)
            self.id_edit_s.setVisible(True)
            self.input_id=''
            self.input_id_valid=0
            
            self.name_edit_s=QLineEdit(self)
            self.name_edit_s.setText('请输入课程名')
            self.name_edit_s.textChanged.connect(self.get_input_name)
            self.name_edit_s.setVisible(True)
            self.input_name=''
            self.input_name_valid=0
            
            self.hour_edit_s=QLineEdit(self)
            self.hour_edit_s.setText('请输入课时数')
            self.hour_edit_s.textChanged.connect(self.get_input_hour)
            self.hour_edit_s.setVisible(True)
            self.input_hour=0
            self.input_hour_valid=0
            
            self.type_sbox_s=QCheckBox('本科生课程',self)
            self.type_bbox_s=QCheckBox('研究生课程',self)
            self.type_sbox_s.stateChanged.connect(self.get_course_type_choice)
            self.type_bbox_s.stateChanged.connect(self.get_course_type_choice)
            self.type_sbox_s.setVisible(True)
            self.type_bbox_s.setVisible(True)
            self.course_type_choice=[]
            self.course_type_condition=''
            self.input_type_valid=0
            
            self.action_button.clicked.connect(self.select_course)
            
            self.id_edit_s.setGeometry(200,200,200,40)
            self.name_edit_s.setGeometry(500,200,200,40)
            self.hour_edit_s.setGeometry(800,200,150,40)
            self.type_sbox_s.setGeometry(1050,200,200,40)
            self.type_bbox_s.setGeometry(1250,200,1200,40)
        
    def remove_simple_select_layout(self):
        if self.table=='Professor':
            self.id_edit_s.setVisible(False)
            self.name_edit_s.setVisible(False)
            self.fbox_s.setVisible(False)
            self.mbox_s.setVisible(False)
            self.output_button.setVisible(False)
            self.year_f_s.setVisible(False)
            self.year_t_s.setVisible(False)
            for e in self.title_box_s:
                e.setVisible(False)
        elif self.table=='Essai':
            self.id_edit_s.setVisible(False)
            self.name_edit_s.setVisible(False)
            self.publish_source_edit_s.setVisible(False)
            self.accept_publish_date_box.setVisible(False)
            self.max_publish_date_edit_s.setVisible(False)
            self.min_publish_date_edit_s.setVisible(False)
            for e in self.type_box_s:
                e.setVisible(False)
            for e in self.rank_box_s:
                e.setVisible(False)
        elif self.table=='Project':
            self.id_edit_s.setVisible(False)
            self.name_edit_s.setVisible(False)
            self.source_edit_s.setVisible(False)
            for e in self.type_box_s:
                e.setVisible(False)
            self.max_funding_edit_s.setVisible(False)
            self.min_funding_edit_s.setVisible(False)
            self.accept_start_date_box.setVisible(False)
            self.accept_end_date_box.setVisible(False)
            self.max_start_date_edit_s.setVisible(False)
            self.min_start_date_edit_s.setVisible(False)
            self.max_end_date_edit_s.setVisible(False)
            self.min_end_date_edit_s.setVisible(False)
        elif self.table=='Course':
            self.id_edit_s.setVisible(False)
            self.name_edit_s.setVisible(False)
            self.hour_edit_s.setVisible(False)
            self.type_sbox_s.setVisible(False)
            self.type_bbox_s.setVisible(False)
        
        self.output_table.setVisible(False)
        self.action_button.setVisible(False)
        self.delete_button.setVisible(False)
        self.update_button.setVisible(False)
        self.back2welcome_button.setVisible(False)
        
    def use_foreign_select_layout(self):
        # 位置和标签暂定
        self.fp_box_s=QCheckBox('显示外键1',self)
        self.fp_box_s.stateChanged.connect(self.change_fp_status)
        self.fp_box_s.setVisible(True)
        
        self.fa_box_s=QCheckBox('显示外键2',self)
        self.fa_box_s.stateChanged.connect(self.change_fa_status)
        self.fa_box_s.setVisible(True)
        
        self.fp_output_table=QTableWidget(self)
        self.fp_output_table.setVisible(False)
        
        self.fa_output_table=QTableWidget(self)
        self.fa_output_table.setVisible(False)
        
        self.foreign_table_status_s=0 # 无，仅有职工外键，仅有其余外键，两个外键均有
        
        self.output_table=QTableWidget(self)
        self.output_table.setVisible(True)
    
        self.action_button=QPushButton('查找',self)
        self.action_button.setVisible(True)
        
        self.delete_button=QPushButton('一键删除',self)
        self.delete_button.clicked.connect(self.delete_select_result)
        self.delete_button.setVisible(True)
        
        self.update_button=QPushButton('一键更新',self)
        self.update_button.clicked.connect(self.change2foreign_update)
        self.update_button.setVisible(True)
        
        self.back2welcome_button=QPushButton('返回',self)
        self.back2welcome_button.clicked.connect(self.back2welcome_foreign_select)
        self.back2welcome_button.setVisible(True)
        
        self.fp_box_s.setGeometry(300,400,200,40)
        self.fa_box_s.setGeometry(600,400,200,40)
        self.output_table.setGeometry(300,500,1400,800)
        self.action_button.setGeometry(550,1400,150,40)
        self.delete_button.setGeometry(800,1400,150,40)
        self.update_button.setGeometry(1050,1400,150,40)
        self.back2welcome_button.setGeometry(1300,1400,150,40)

        if self.table=='Publish':
            self.fp_table='Professor'
            self.fa_table='Essai'
            
            self.id_edit_p_s=QLineEdit(self)
            self.id_edit_p_s.setText('请输入工号')
            self.id_edit_p_s.textChanged.connect(self.get_input_fp_ID)
            self.id_edit_p_s.setVisible(True)
            self.input_fp_id=''
            self.input_fp_id_valid=0
            
            self.id_edit_f_s=QLineEdit(self)
            self.id_edit_f_s.setText('请输入编号')
            self.id_edit_f_s.textChanged.connect(self.get_input_fa_ID_number)
            self.id_edit_f_s.setVisible(True)
            self.input_fa_id=0
            self.input_fa_id_valid=0
            
            self.min_seq_edit_s=QLineEdit(self)
            self.min_seq_edit_s.setText('请输入作者排名下界')
            self.min_seq_edit_s.textChanged.connect(self.get_min_author_rank)
            self.min_seq_edit_s.setVisible(True)
            self.input_min_author_rank=0
            self.input_min_author_rank_valid=0
            
            self.max_seq_edit_s=QLineEdit(self)
            self.max_seq_edit_s.setText('请输入作者排名上界')
            self.max_seq_edit_s.textChanged.connect(self.get_max_author_rank)
            self.max_seq_edit_s.setVisible(True)
            self.input_max_author_rank=0
            self.input_max_author_rank_valid=0
            
            self.accept_author_rank_box=QCheckBox('检测作者排名',self)
            self.accept_author_rank_box.stateChanged.connect(self.swap_accept_author_rank)
            self.accept_author_rank_box.setVisible(True)
            self.min_seq_edit_s.setEnabled(False)
            self.max_seq_edit_s.setEnabled(False)
            
            self.input_author_rank_valid=0
            self.author_rank_condition=''
            
            self.comm_author_box_s=QCheckBox('是否为通讯作者',self)
            self.comm_author_box_s.stateChanged.connect(self.swap_comm_author)
            self.comm_author_box_s.setVisible(True)
            self.input_is_comm_author=0
            self.input_is_comm_author_valid=0
            
            self.action_button.clicked.connect(self.select_publish)
            
            self.id_edit_p_s.setGeometry(200,200,200,40)
            self.id_edit_f_s.setGeometry(500,200,200,40)
            self.comm_author_box_s.setGeometry(800,200,200,40)
            self.accept_author_rank_box.setGeometry(200,300,200,40)
            self.min_seq_edit_s.setGeometry(500,300,200,40)
            self.max_seq_edit_s.setGeometry(800,300,200,40)
        elif self.table=='Undertake':
            self.fp_table='Professor'
            self.fa_table='Project'
            
            self.id_edit_p_s=QLineEdit(self)
            self.id_edit_p_s.setText('请输入工号')
            self.id_edit_p_s.textChanged.connect(self.get_input_fp_ID)
            self.id_edit_p_s.setVisible(True)
            self.input_fp_id=''
            self.input_fp_id_valid=0
            
            self.id_edit_f_s=QLineEdit(self)
            self.id_edit_f_s.setText('请输入项目号')
            self.id_edit_f_s.textChanged.connect(self.get_input_fa_ID)
            self.id_edit_f_s.setVisible(True)
            self.input_fa_id=''
            self.input_fa_id_valid=0
            
            self.min_seq_edit_s=QLineEdit(self)
            self.min_seq_edit_s.setText('请输入承担排名下界')
            self.min_seq_edit_s.textChanged.connect(self.get_min_res_rank)
            self.min_seq_edit_s.setVisible(True)
            self.input_min_res_rank=0
            self.input_min_res_rank_valid=0
            
            self.max_seq_edit_s=QLineEdit(self)
            self.max_seq_edit_s.setText('请输入承担排名上界')
            self.max_seq_edit_s.textChanged.connect(self.get_max_res_rank)
            self.max_seq_edit_s.setVisible(True)
            self.input_max_res_rank=0
            self.input_max_res_rank_valid=0
            
            self.accept_res_rank_box=QCheckBox('检测承担排名',self)
            self.accept_res_rank_box.stateChanged.connect(self.swap_accept_res_rank)
            self.accept_res_rank_box.setVisible(True)
            self.min_seq_edit_s.setEnabled(False)
            self.max_seq_edit_s.setEnabled(False)
            
            self.input_res_rank_valid=0
            self.res_rank_condition=''
            
            self.min_res_funding_edit_s=QLineEdit(self)
            self.min_res_funding_edit_s.setText('请输入承担经费下界')
            self.min_res_funding_edit_s.textChanged.connect(self.get_min_res_funding)
            self.min_res_funding_edit_s.setVisible(True)
            self.input_min_res_funding=0.0
            self.input_min_res_funding_valid=0
            
            self.max_res_funding_edit_s=QLineEdit(self)
            self.max_res_funding_edit_s.setText('请输入承担经费上界')
            self.max_res_funding_edit_s.textChanged.connect(self.get_max_res_funding)
            self.max_res_funding_edit_s.setVisible(True)
            self.input_max_res_funding=0.0
            self.input_max_res_funding_valid=0
            
            self.accept_res_funding_box=QCheckBox('检测承担经费',self)
            self.accept_res_funding_box.stateChanged.connect(self.swap_accept_res_funding)
            self.accept_res_funding_box.setVisible(True)
            self.min_res_funding_edit_s.setEnabled(False)
            self.max_res_funding_edit_s.setEnabled(False)
            
            self.action_button.clicked.connect(self.select_undertake)
            
            self.id_edit_p_s.setGeometry(200,200,200,40)
            self.id_edit_f_s.setGeometry(500,200,200,40)
            self.accept_res_rank_box.setGeometry(100,300,200,40)
            self.min_seq_edit_s.setGeometry(350,300,250,40)
            self.max_seq_edit_s.setGeometry(650,300,250,40)
            self.accept_res_funding_box.setGeometry(1000,300,200,40)
            self.min_res_funding_edit_s.setGeometry(1250,300,250,40)
            self.max_res_funding_edit_s.setGeometry(1550,300,250,40)
        elif self.table=='Teach':
            self.fp_table='Professor'
            self.fa_table='Course'
            
            self.id_edit_p_s=QLineEdit(self)
            self.id_edit_p_s.setText('请输入工号')
            self.id_edit_p_s.textChanged.connect(self.get_input_fp_ID)
            self.id_edit_p_s.setVisible(True)
            self.input_fp_id=''
            self.input_fp_id_valid=0
            
            self.id_edit_f_s=QLineEdit(self)
            self.id_edit_f_s.setText('请输入编号')
            self.id_edit_f_s.textChanged.connect(self.get_input_fa_ID)
            self.id_edit_f_s.setVisible(True)
            self.input_fa_id=''
            self.input_fa_id_valid=0
            
            self.course_year_box_s=QComboBox(self)
            self.course_year_box_s.addItems([str(i) for i in self.year_list])
            self.course_year_box_s.currentIndexChanged.connect(self.get_input_year)
            self.course_year_box_s.setVisible(True)
            self.input_year=self.year_list[0]
            self.input_year_valid=1
            
            # 用列表保存所有可能的类型
            self.semester_box_s=[]
            for e in semesters:
                self.semester_box_s.append(QCheckBox(e,self))
                idx=semesters.index(e)
                self.semester_box_s[idx].stateChanged.connect(self.get_semester_choice)
                self.semester_box_s[idx].setVisible(True)
            self.semester_choice=''
            self.semester_condition=''
            self.input_semester_valid=0
            
            self.min_res_hour_edit_s=QLineEdit(self)
            self.min_res_hour_edit_s.setText('请输入负责课时数下界')
            self.min_res_hour_edit_s.textChanged.connect(self.get_min_res_hour)
            self.min_res_hour_edit_s.setVisible(True)
            self.input_min_res_hour=0
            self.input_min_res_hour_valid=0
            
            self.max_res_hour_edit_s=QLineEdit(self)
            self.max_res_hour_edit_s.setText('请输入负责课时数上界')
            self.max_res_hour_edit_s.textChanged.connect(self.get_max_res_hour)
            self.max_res_hour_edit_s.setVisible(True)
            self.input_max_res_hour=0
            self.input_max_res_hour_valid=0
            
            self.accept_res_hour_box=QCheckBox('检测课时数',self)
            self.accept_res_hour_box.stateChanged.connect(self.swap_accept_res_hour)
            self.accept_res_hour_box.setVisible(True)
            self.min_res_hour_edit_s.setEnabled(False)
            self.max_res_hour_edit_s.setEnabled(False)
            
            self.action_button.clicked.connect(self.select_teach)
            
            self.id_edit_p_s.setGeometry(200,200,200,40)
            self.id_edit_f_s.setGeometry(500,200,200,40)
            self.course_year_box_s.setGeometry(800,200,150,40)
            for e in self.semester_box_s:
                idx=self.semester_box_s.index(e)
                e.setGeometry(1050+idx*300,200,200,40)
            self.accept_res_hour_box.setGeometry(200,300,200,40)
            self.min_res_hour_edit_s.setGeometry(500,300,250,40)
            self.max_res_hour_edit_s.setGeometry(800,300,250,40)
                
    def remove_foreign_select_layout(self):
        if self.table=='Publish':
            self.id_edit_p_s.setVisible(False)
            self.id_edit_f_s.setVisible(False)
            self.accept_author_rank_box.setVisible(False)
            self.min_seq_edit_s.setVisible(False)
            self.max_seq_edit_s.setVisible(False)
            self.comm_author_box_s.setVisible(False)
        elif self.table=='Undertake':
            self.id_edit_p_s.setVisible(False)
            self.id_edit_f_s.setVisible(False)
            self.accept_res_rank_box.setVisible(False)
            self.min_seq_edit_s.setVisible(False)
            self.max_seq_edit_s.setVisible(False)
            self.accept_res_funding_box.setVisible(False)
            self.min_res_funding_edit_s.setVisible(False)
            self.max_res_funding_edit_s.setVisible(False)
        elif self.table=='Teach':
            self.id_edit_p_s.setVisible(False)
            self.id_edit_f_s.setVisible(False)
            self.course_year_box_s.setVisible(False)
            for e in self.semester_box_s:
                e.setVisible(False)
            self.min_res_hour_edit_s.setVisible(False)
            self.max_res_hour_edit_s.setVisible(False)
            self.accept_res_hour_box.setVisible(False)
        
        self.fp_box_s.setVisible(False)
        self.fa_box_s.setVisible(False)
        self.fp_output_table.setVisible(False)
        self.fa_output_table.setVisible(False)
        self.output_table.setVisible(False)
        self.action_button.setVisible(False)
        self.delete_button.setVisible(False)
        self.update_button.setVisible(False)
        self.back2welcome_button.setVisible(False)
    
    def change2foreign_update(self):
        self.operation='update'
        
        self.action_button.setVisible(False)
        self.delete_button.setVisible(False)
        self.update_button.setVisible(False)
        self.back2welcome_button.setVisible(False)
        
        self.fp_box_s.setChecked(False)
        self.fa_box_s.setChecked(False)
        self.fp_box_s.setVisible(False)
        self.fa_box_s.setVisible(False)
        self.foreign_table_status=0
        self.foreign_table_status_changed()
        
        self.output_table.setGeometry(200,850,1400,450)
        
        self.action_button=QPushButton('全部更新',self)
        self.action_button.setVisible(True)
        
        self.back2select_button=QPushButton('返回',self)
        self.back2select_button.clicked.connect(self.back2foreign_select)
        self.back2select_button.setVisible(True)
        
        self.action_button.setGeometry(550,1400,150,40)
        self.back2select_button.setGeometry(1300,1400,150,40)
        if self.table=='Publish':
            self.id_edit_p_s.setEnabled(False)
            self.id_edit_f_s.setEnabled(False)
            self.accept_author_rank_box.setEnabled(False)
            self.min_seq_edit_s.setEnabled(False)
            self.max_seq_edit_s.setEnabled(False)
            self.comm_author_box_s.setEnabled(False)
        
            self.id_edit_p=QLineEdit(self)
            self.id_edit_p.setText('请输入工号')
            self.id_edit_p.textChanged.connect(self.get_input_fp_ID)
            self.id_edit_p.setVisible(True)
            self.input_fp_id=''
            self.input_fp_id_valid_update=0
            
            self.id_edit_f=QLineEdit(self)
            self.id_edit_f.setText('请输入编号')
            self.id_edit_f.textChanged.connect(self.get_input_fa_ID_number)
            self.id_edit_f.setVisible(True)
            self.input_fa_id_number=0
            self.input_fa_id_valid_update=0
            
            self.seq_edit=QLineEdit(self)
            self.seq_edit.setText('请输入作者排名')
            self.seq_edit.textChanged.connect(self.get_author_rank)
            self.seq_edit.setVisible(True)
            self.input_author_rank=''
            self.input_author_rank_valid_update=0
            
            self.comm_author_box=QCheckBox('是否为通讯作者',self)
            self.comm_author_box.stateChanged.connect(self.swap_comm_author)
            self.comm_author_box.setVisible(True)
            self.input_is_comm_author=0
            self.input_is_comm_author_valid_update=1
            
            self.action_button.clicked.connect(self.update_publish)
            
            self.id_edit_p.setGeometry(200,400,200,40)
            self.id_edit_f.setGeometry(500,400,200,40)
            self.seq_edit.setGeometry(800,400,200,40)
            self.comm_author_box.setGeometry(1100,400,200,40)
        elif self.table=='Undertake':
            self.id_edit_p_s.setEnabled(False)
            self.id_edit_f_s.setEnabled(False)
            self.accept_res_rank_box.setEnabled(False)
            self.min_seq_edit_s.setEnabled(False)
            self.max_seq_edit_s.setEnabled(False)
            self.accept_res_funding_box.setEnabled(False)
            self.min_res_funding_edit_s.setEnabled(False)
            self.max_res_funding_edit_s.setEnabled(False)
        
            self.id_edit_p=QLineEdit(self)
            self.id_edit_p.setText('请输入工号')
            self.id_edit_p.textChanged.connect(self.get_input_fp_ID)
            self.id_edit_p.setVisible(True)
            self.input_fp_id=''
            self.input_fp_id_valid_update=0
            
            self.id_edit_f=QLineEdit(self)
            self.id_edit_f.setText('请输入项目号')
            self.id_edit_f.textChanged.connect(self.get_input_fa_ID)
            self.id_edit_f.setVisible(True)
            self.input_fa_id=''
            self.input_fa_id_valid_update=0
            
            self.seq_edit=QLineEdit(self)
            self.seq_edit.setText('请输入承担排名')
            self.seq_edit.textChanged.connect(self.get_res_rank)
            self.seq_edit.setVisible(True)
            self.input_res_rank=0
            self.input_res_rank_valid_update=0
            
            self.res_funding_edit=QLineEdit(self)
            self.res_funding_edit.setText('请输入承担经费')
            self.res_funding_edit.textChanged.connect(self.get_input_funding)
            self.res_funding_edit.setVisible(True)
            self.input_funding=0.0
            self.input_funding_valid_update=0
            
            self.action_button.clicked.connect(self.update_undertake)
            
            self.id_edit_p.setGeometry(200,400,200,40)
            self.id_edit_f.setGeometry(500,400,200,40)
            self.seq_edit.setGeometry(800,400,200,40)
            self.res_funding_edit.setGeometry(1100,400,200,40)
        elif self.table=='Teach':
            self.id_edit_p_s.setEnabled(False)
            self.id_edit_f_s.setEnabled(False)
            self.course_year_box_s.setEnabled(False)
            for e in self.semester_box_s:
                e.setEnabled(False)
            self.min_res_hour_edit_s.setEnabled(False)
            self.max_res_hour_edit_s.setEnabled(False)
            self.accept_res_hour_box.setEnabled(False)
            
            self.id_edit_p=QLineEdit(self)
            self.id_edit_p.setText('请输入工号')
            self.id_edit_p.textChanged.connect(self.get_input_fp_ID)
            self.id_edit_p.setVisible(True)
            self.input_fp_id=''
            self.input_fp_id_valid_update=0
            
            self.id_edit_f=QLineEdit(self)
            self.id_edit_f.setText('请输入编号')
            self.id_edit_f.textChanged.connect(self.get_input_fa_ID)
            self.id_edit_f.setVisible(True)
            self.input_fa_id=''
            self.input_fa_id_valid_update=0
            
            self.course_year_box=QComboBox(self)
            self.course_year_box.addItems([str(i) for i in self.year_list])
            self.course_year_box.currentIndexChanged.connect(self.get_input_year)
            self.course_year_box.setVisible(True)
            self.input_year=self.year_list[0]
            self.input_year_valid_update=1
            
            # 可以增加一个根据当前日期自动确定当前学期的功能
            self.semester_box=QComboBox(self)
            self.semester_box.addItems(semesters)
            self.semester_box.currentIndexChanged.connect(self.get_input_semester)
            self.semester_box.setVisible(True)
            self.input_semester=1
            self.input_semester_valid_update=1
            
            self.res_hour_edit=QLineEdit(self)
            self.res_hour_edit.setText('请输入负责课时数')
            self.res_hour_edit.textChanged.connect(self.get_input_hour)
            self.res_hour_edit.setVisible(True)
            self.input_hour=0
            self.input_hour_valid_update=0
            
            self.action_button.clicked.connect(self.update_teach)
                
            self.id_edit_p.setGeometry(200,400,200,40)
            self.id_edit_f.setGeometry(500,400,200,40)
            self.course_year_box.setGeometry(800,400,150,40)
            self.semester_box.setGeometry(1050,400,200,40)
            self.res_hour_edit.setGeometry(1350,400,250,40)
            
    def back2foreign_select(self):
        self.operation='select'
        
        self.output_table.setGeometry(200,500,1400,800)
        
        self.action_button.setVisible(True)
        self.delete_button.setVisible(True)
        self.update_button.setVisible(True)
        self.back2welcome_button.setVisible(True)
        
        self.fp_box_s.setVisible(True)
        self.fa_box_s.setVisible(True)
        
        self.action_button.setVisible(False)
        self.back2select_button.setVisible(False)
        self.action_button=QPushButton('查找',self)
        self.action_button.setVisible(True)
        self.action_button.setGeometry(550,1400,150,40)
        if self.table=='Publish':
            self.id_edit_p_s.setEnabled(True)
            self.id_edit_f_s.setEnabled(True)
            self.accept_author_rank_box.setEnabled(True)
            self.min_seq_edit_s.setEnabled(True)
            self.max_seq_edit_s.setEnabled(True)
            self.comm_author_box_s.setEnabled(True)
        
            self.id_edit_p.setVisible(False)
            self.id_edit_f.setVisible(False)
            self.seq_edit.setVisible(False)
            self.comm_author_box.setVisible(False)
            
            self.action_button.clicked.connect(self.select_publish)
        elif self.table=='Undertake':
            self.id_edit_p_s.setEnabled(True)
            self.id_edit_f_s.setEnabled(True)
            self.accept_res_rank_box.setEnabled(True)
            self.min_seq_edit_s.setEnabled(True)
            self.max_seq_edit_s.setEnabled(True)
            self.accept_res_funding_box.setEnabled(True)
            self.min_res_funding_edit_s.setEnabled(True)
            self.max_res_funding_edit_s.setEnabled(True)
        
            self.id_edit_p.setVisible(False)
            self.id_edit_f.setVisible(False)
            self.seq_edit.setVisible(False)
            self.res_funding_edit.setVisible(False)
            
            self.action_button.clicked.connect(self.select_undertake)
        elif self.table=='Teach':
            self.id_edit_p_s.setEnabled(True)
            self.id_edit_f_s.setEnabled(True)
            self.course_year_box_s.setEnabled(True)
            for e in self.semester_box_s:
                e.setEnabled(True)
            self.min_res_hour_edit_s.setEnabled(True)
            self.max_res_hour_edit_s.setEnabled(True)
            self.accept_res_hour_box.setEnabled(True)
            
            self.id_edit_p.setVisible(False)
            self.id_edit_f.setVisible(False)
            self.course_year_box.setVisible(False)
            self.semester_box.setVisible(False)
            self.res_hour_edit.setVisible(False)
            
            self.action_button.clicked.connect(self.select_teach)
        
    def change2simple_update(self):
        self.operation='update'
        
        self.output_table.setGeometry(200,850,1400,450)
        
        self.action_button.setVisible(False)
        self.delete_button.setVisible(False)
        self.update_button.setVisible(False)
        self.back2welcome_button.setVisible(False)
        
        self.action_button=QPushButton('全部更新',self)
        self.action_button.setVisible(True)
        
        self.back2select_button=QPushButton('返回',self)
        self.back2select_button.clicked.connect(self.back2simple_select)
        self.back2select_button.setVisible(True)
        
        self.action_button.setGeometry(550,1400,150,40)
        self.back2select_button.setGeometry(1300,1400,150,40)
        if self.table=='Professor':
            self.id_edit_s.setEnabled(False)
            self.name_edit_s.setEnabled(False)
            self.fbox_s.setEnabled(False)
            self.mbox_s.setEnabled(False)
            for e in self.title_box_s:
                e.setEnabled(False)
            self.output_button.setVisible(False)
            self.year_f_s.setEnabled(False)
            self.year_t_s.setEnabled(False)
            
            self.id_edit=QLineEdit(self)
            self.id_edit.setText('请输入工号')
            self.id_edit.textChanged.connect(self.get_input_ID)
            self.id_edit.setVisible(True)
            self.input_id=''
            self.input_id_valid_update=0
            
            self.name_edit=QLineEdit(self)
            self.name_edit.setText('请输入姓名')
            self.name_edit.textChanged.connect(self.get_input_name)
            self.name_edit.setVisible(True)
            self.input_name=''
            self.input_name_valid_update=0
            
            self.fradio=QRadioButton('女',self)
            self.mradio=QRadioButton('男',self)
            self.fradio.setChecked(True)
            self.fradio.toggled.connect(self.swap_gender)
            self.mradio.toggled.connect(self.swap_gender)
            self.fradio.setVisible(True)
            self.mradio.setVisible(True)
            self.input_gender=2
            self.input_gender_valid_update=1
            
            self.title_box=QComboBox(self)
            self.title_box.addItem('职称')
            self.title_box.addItems(titles)
            self.title_box.currentIndexChanged.connect(self.get_input_title)
            self.title_box.setVisible(True)
            self.input_title=0
            self.input_title_valid_update=0
            
            self.action_button.clicked.connect(self.update_professor)
            
            self.id_edit.setGeometry(200,500,200,40)
            self.name_edit.setGeometry(500,500,200,40)
            self.fradio.setGeometry(800,500,100,40)
            self.mradio.setGeometry(950,500,100,40)
            self.title_box.setGeometry(1100,500,200,40)
            
        elif self.table=='Essai':
            self.id_edit_s.setEnabled(False)
            self.name_edit_s.setEnabled(False)
            self.publish_source_edit_s.setEnabled(False)
            self.max_publish_date_edit_s.setEnabled(False)
            self.min_publish_date_edit_s.setEnabled(False)
            self.accept_publish_date_box.setEnabled(False)
            for e in self.type_box_s:
                e.setEnabled(False)
            for e in self.rank_box_s:
                e.setEnabled(False)
            
            self.id_edit=QLineEdit(self)
            self.id_edit.setText('请输入编号')
            self.id_edit.textChanged.connect(self.get_input_ID_number)
            self.id_edit.setVisible(True)
            self.input_id_number=0
            self.input_id_valid_update=0
            
            self.name_edit=QLineEdit(self)
            self.name_edit.setText('请输入论文标题')
            self.name_edit.textChanged.connect(self.get_input_name)
            self.name_edit.setVisible(True)
            self.input_name=''
            self.input_name_valid_update=0
            
            self.publish_source_edit=QLineEdit(self)
            self.publish_source_edit.setText('请输入发表源')
            self.publish_source_edit.textChanged.connect(self.get_input_source)
            self.publish_source_edit.setVisible(True)
            self.input_source=''
            self.input_source_valid_update=0
            
            self.publish_date_edit=QDateEdit(self)
            self.publish_date_edit.setMaximumDate(QDate.currentDate())
            self.publish_date_edit.setDate(QDate.currentDate())
            self.publish_date_edit.dateChanged.connect(self.get_publish_date)
            self.publish_date_edit.setVisible(True)
            year=str(QDate.currentDate().year())
            month=str(QDate.currentDate().month())
            day=str(QDate.currentDate().day())
            self.input_publish_date=year+'/'+month+'/'+day
            self.input_publish_date_valid_update=0
            
            self.type_box=QComboBox(self)
            self.type_box.addItem('论文类型')
            self.type_box.addItems(essai_type)
            self.type_box.currentIndexChanged.connect(self.get_input_type)
            self.type_box.setVisible(True)
            self.input_type=0
            self.input_type_valid_update=0
            
            self.rank_box=QComboBox(self)
            self.rank_box.addItem('论文级别')
            self.rank_box.addItems(essai_rank)
            self.rank_box.currentIndexChanged.connect(self.get_input_rank)
            self.rank_box.setVisible(True)
            self.input_rank=0
            self.input_rank_valid_update=0
            
            self.action_button.clicked.connect(self.update_essai)
            
            self.id_edit.setGeometry(200,500,200,40)
            self.name_edit.setGeometry(500,500,500,40)
            self.publish_source_edit.setGeometry(200,600,1000,40)
            self.publish_date_edit.setGeometry(200,700,300,40)
            self.type_box.setGeometry(650,700,200,40)
            self.rank_box.setGeometry(1000,700,200,40)
            
        elif self.table=='Project':
            self.id_edit_s.setEnabled(False)
            self.name_edit_s.setEnabled(False)
            self.source_edit_s.setEnabled(False)
            for e in self.type_box_s:
                e.setEnabled(False)
            self.max_funding_edit_s.setEnabled(False)
            self.min_funding_edit_s.setEnabled(False)
            self.accept_start_date_box.setEnabled(False)
            self.accept_end_date_box.setEnabled(False)
            self.max_start_date_edit_s.setEnabled(False)
            self.min_start_date_edit_s.setEnabled(False)
            self.max_end_date_edit_s.setEnabled(False)
            self.min_end_date_edit_s.setEnabled(False)
            
            self.id_edit=QLineEdit(self)
            self.id_edit.setText('请输入项目号')
            self.id_edit.textChanged.connect(self.get_input_ID)
            self.id_edit.setVisible(True)
            self.input_id=''
            self.input_id_valid_update=0
            
            self.name_edit=QLineEdit(self)
            self.name_edit.setText('请输入项目名称')
            self.name_edit.textChanged.connect(self.get_input_name)
            self.name_edit.setVisible(True)
            self.input_name=''
            self.input_name_valid_update=0
            
            self.source_edit=QLineEdit(self)
            self.source_edit.setText('请输入项目来源')
            self.source_edit.textChanged.connect(self.get_input_source)
            self.source_edit.setVisible(True)
            self.input_source=''
            self.input_source_valid_update=0
            
            self.type_box=QComboBox(self)
            self.type_box.addItem('项目类型')
            self.type_box.addItems(project_type)
            self.type_box.currentIndexChanged.connect(self.get_input_type)
            self.type_box.setVisible(True)
            self.input_type=0
            self.input_type_valid_update=0
            
            self.total_funding_edit=QLineEdit(self)
            self.total_funding_edit.setText('请输入总经费')
            self.total_funding_edit.setVisible(True)
            self.total_funding_edit.textChanged.connect(self.get_input_funding)
            self.input_funding=0.0
            self.input_funding_valid_update=0
            
            self.start_date_edit=QDateEdit(self)
            self.start_date_edit.setMaximumDate(QDate.currentDate())
            self.start_date_edit.setDate(QDate.currentDate())
            self.start_date_edit.dateChanged.connect(self.get_start_date)
            self.start_date_edit.setVisible(True)
            year=str(QDate.currentDate().year())
            month=str(QDate.currentDate().month())
            day=str(QDate.currentDate().day())
            self.input_start_date=year+'/'+month+'/'+day
            self.input_start_date_valid_update=0
            
            self.end_date_edit=QDateEdit(self)
            self.end_date_edit.setDate(QDate.currentDate())
            self.end_date_edit.dateChanged.connect(self.get_end_date)
            self.end_date_edit.setVisible(True)
            year=str(QDate.currentDate().year())
            month=str(QDate.currentDate().month())
            day=str(QDate.currentDate().day())
            self.input_end_date=year+'/'+month+'/'+day
            self.input_end_date_valid_update=0
            
            self.action_button.clicked.connect(self.update_project)
            
            self.id_edit.setGeometry(200,500,200,40)
            self.name_edit.setGeometry(500,500,200,40)
            self.source_edit.setGeometry(200,600,1000,40)
            self.type_box.setGeometry(200,700,200,40)
            self.total_funding_edit.setGeometry(500,700,200,40)
            self.start_date_edit.setGeometry(800,700,200,40)
            self.end_date_edit.setGeometry(1100,700,200,40)
            
        elif self.table=='Course':
            self.id_edit_s.setEnabled(False)
            self.name_edit_s.setEnabled(False)
            self.hour_edit_s.setEnabled(False)
            self.type_sbox_s.setEnabled(False)
            self.type_bbox_s.setEnabled(False)
            
            self.id_edit=QLineEdit(self)
            self.id_edit.setText('请输入编号')
            self.id_edit.textChanged.connect(self.get_input_ID)
            self.id_edit.setVisible(True)
            self.input_id=''
            self.input_id_valid_update=0
            
            self.name_edit=QLineEdit(self)
            self.name_edit.setText('请输入课程名')
            self.name_edit.textChanged.connect(self.get_input_name)
            self.name_edit.setVisible(True)
            self.input_name=''
            self.input_name_valid_update=0
            
            self.hour_edit=QLineEdit(self)
            self.hour_edit.setText('请输入课时数')
            self.hour_edit.textChanged.connect(self.get_input_hour)
            self.hour_edit.setVisible(True)
            self.input_hour=0
            self.input_hour_valid_update=0
            
            self.type_sradio=QRadioButton('本科生课程',self)
            self.type_bradio=QRadioButton('研究生课程',self)
            self.type_sradio.setChecked(True)
            self.type_sradio.toggled.connect(self.swap_course_type)
            self.type_bradio.toggled.connect(self.swap_course_type)
            self.type_sradio.setVisible(True)
            self.type_bradio.setVisible(True)
            self.input_type=1
            self.input_type_valid_update=1
            
            self.action_button.clicked.connect(self.update_course)
            
            self.id_edit.setGeometry(200,500,200,40)
            self.name_edit.setGeometry(500,500,200,40)
            self.hour_edit.setGeometry(800,500,150,40)
            self.type_sradio.setGeometry(1050,500,200,40)
            self.type_bradio.setGeometry(1250,500,1200,40)
        
    def back2simple_select(self):
        self.operation='select'

        self.output_table.setGeometry(200,500,1400,800)
        
        self.delete_button.setVisible(True)
        self.update_button.setVisible(True)
        self.back2welcome_button.setVisible(True)
        self.action_button.setVisible(False)
        self.back2select_button.setVisible(False)
        
        self.action_button=QPushButton('查找',self)
        self.action_button.setVisible(True)
        self.action_button.setGeometry(550,1400,150,40)
        
        if self.table=='Professor':
            self.id_edit_s.setEnabled(True)
            self.name_edit_s.setEnabled(True)
            self.fbox_s.setEnabled(True)
            self.mbox_s.setEnabled(True)
            for e in self.title_box_s:
                e.setEnabled(True)
            self.output_button.setVisible(True)
            self.year_f_s.setEnabled(True)
            self.year_t_s.setEnabled(True)
            self.action_button.setGeometry(450,1400,150,40)
            
            self.id_edit.setVisible(False)
            self.name_edit.setVisible(False)
            self.fradio.setChecked(False)
            self.fradio.setVisible(False)
            self.mradio.setVisible(False)
            self.title_box.setVisible(False)
            
            self.action_button.clicked.connect(self.select_professor)
            
        elif self.table=='Essai':
            self.id_edit_s.setEnabled(True)
            self.name_edit_s.setEnabled(True)
            self.publish_source_edit_s.setEnabled(True)
            self.accept_publish_date_box.setEnabled(True)
            if self.accept_publish_date_box.isChecked():
                self.max_publish_date_edit_s.setEnabled(True)
                self.min_publish_date_edit_s.setEnabled(True)
            for e in self.type_box_s:
                e.setEnabled(True)
            for e in self.rank_box_s:
                e.setEnabled(True)
            
            self.id_edit.setVisible(False)
            self.name_edit.setVisible(False)
            self.publish_source_edit.setVisible(False)
            self.publish_date_edit.setVisible(False)
            self.type_box.setVisible(False)
            self.rank_box.setVisible(False)
            
            self.action_button.clicked.connect(self.select_essai)
            
        elif self.table=='Project':
            self.id_edit_s.setEnabled(True)
            self.name_edit_s.setEnabled(True)
            self.source_edit_s.setEnabled(True)
            for e in self.type_box_s:
                e.setEnabled(True)
            self.max_funding_edit_s.setEnabled(True)
            self.min_funding_edit_s.setEnabled(True)
            self.accept_start_date_box.setEnabled(True)
            self.accept_end_date_box.setEnabled(True)
            if self.accept_start_date_box.isChecked():
                self.max_start_date_edit_s.setEnabled(True)
                self.min_start_date_edit_s.setEnabled(True)
            if self.accept_end_date_box.isChecked():
                self.max_end_date_edit_s.setEnabled(True)
                self.min_end_date_edit_s.setEnabled(True)
            
            self.id_edit.setVisible(False)
            self.name_edit.setVisible(False)
            self.source_edit.setVisible(False)
            self.type_box.setVisible(False)
            self.total_funding_edit.setVisible(False)
            self.start_date_edit.setVisible(False)
            self.end_date_edit.setVisible(False)
            
            self.action_button.clicked.connect(self.select_project)
            
        elif self.table=='Course':
            self.id_edit_s.setEnabled(True)
            self.name_edit_s.setEnabled(True)
            self.hour_edit_s.setEnabled(True)
            self.type_sbox_s.setEnabled(True)
            self.type_bbox_s.setEnabled(True)
            
            self.id_edit.setVisible(False)
            self.name_edit.setVisible(False)
            self.hour_edit.setVisible(False)
            self.type_sradio.setChecked(False)
            self.type_sradio.setVisible(False)
            self.type_bradio.setVisible(False)
            
            self.action_button.clicked.connect(self.select_course)
        
    def change_fp_status_insert(self,is_checked):
        if is_checked==Qt.Checked:
            self.foreign_table_status+=1
            self.foreign_table_status%=4
        else:
            self.foreign_table_status-=1
            self.foreign_table_status%=4
        self.foreign_table_status_changed_insert()
        
    def change_fa_status_insert(self,is_checked):
        if is_checked==Qt.Checked:
            self.foreign_table_status+=2
            self.foreign_table_status%=4
        else:
            self.foreign_table_status-=2
            self.foreign_table_status%=4
        self.foreign_table_status_changed_insert()
        
    def foreign_table_status_changed_insert(self):
        if self.foreign_table_status==0:
            self.fp_output_table.setVisible(False)
            self.fa_output_table.setVisible(False)
        elif self.foreign_table_status==1:
            self.fp_output_table.setVisible(True)
            self.fa_output_table.setVisible(False)
            self.fp_output_table.setGeometry(300,500,1400,200)
        elif self.foreign_table_status==2:
            self.fp_output_table.setVisible(False)
            self.fa_output_table.setVisible(True)
            self.fa_output_table.setGeometry(300,500,1400,200)
        elif self.foreign_table_status==3:
            self.fp_output_table.setVisible(True)
            self.fa_output_table.setVisible(True)
            self.fp_output_table.setGeometry(300,500,700,200)
            self.fa_output_table.setGeometry(1000,500,700,200)
        
    def change_fp_status(self,is_checked):
        if is_checked==Qt.Checked:
            self.foreign_table_status_s+=1
            self.foreign_table_status_s%=4
        else:
            self.foreign_table_status_s-=1
            self.foreign_table_status_s%=4
        self.foreign_table_status_changed()
        
    def change_fa_status(self,is_checked):
        if is_checked==Qt.Checked:
            self.foreign_table_status_s+=2
            self.foreign_table_status_s%=4
        else:
            self.foreign_table_status_s-=2
            self.foreign_table_status_s%=4
        self.foreign_table_status_changed()
        
    def foreign_table_status_changed(self):
        if self.foreign_table_status_s==0:
            self.fp_output_table.setVisible(False)
            self.fa_output_table.setVisible(False)
            self.output_table.setVisible(True)
            self.output_table.setGeometry(300,500,1400,800)
        elif self.foreign_table_status_s==1:
            self.fp_output_table.setVisible(True)
            self.fa_output_table.setVisible(False)
            self.output_table.setVisible(True)
            self.fp_output_table.setGeometry(300,500,1400,200)
            self.output_table.setGeometry(300,720,1400,580)
        elif self.foreign_table_status_s==2:
            self.fp_output_table.setVisible(False)
            self.fa_output_table.setVisible(True)
            self.output_table.setVisible(True)
            self.fa_output_table.setGeometry(300,500,1400,200)
            self.output_table.setGeometry(300,720,1400,580)
        elif self.foreign_table_status_s==3:
            self.fp_output_table.setVisible(True)
            self.fa_output_table.setVisible(True)
            self.output_table.setVisible(True)
            self.fp_output_table.setGeometry(300,500,700,200)
            self.fa_output_table.setGeometry(1000,500,700,200)
            self.output_table.setGeometry(300,720,1400,580)
            
    # 一些特殊处理
    # 查找同排名作者，以避免出现作者相同排名的情况
    # 注意在批量更新时，应当同时检查排名情况
    def select_author_rank(self):
        keys=['Essai_id','Author_Sequence']
        values=[self.current_essai_id,self.current_rank]
        
        l=convert_key_value(keys,values)
            
        condition=convert_and_condition(l)
        
        db=self.db
        table=self.table # 注意这里table应当恒为'Publish'
        
        n,l=select(db,table,condition)
        
        return n,l
    
    # 查找通讯作者：在使用过程中，需要判断是否可能出现两位通讯作者
    def select_comm_author(self):
        #查找的条件应当是，论文编号等于输入的论文编号（注意修改时可能修改一批文章，这时需要迭代查询），并标记“是通讯作者”，若查找到结果，说明已经有了通讯作者
        keys=['Essai_ID','Is_Comm_Author']
        values=[self.current_essai_id,1]
        
        l=convert_key_value(keys,values)
            
        condition=convert_and_condition(l)
        
        db=self.db
        table=self.table # 注意这里table应当恒为'Publish'
        
        n,l=select(db,table,condition)
        
        return n,l
    
    # 改变通讯作者：在使用过程中，若在插入/通讯作者的时候检测到已经有通讯作者，应当能支持一键修改通讯作者
    def change_comm_author(self):
        org_work_id=self.org_work_id
        conflict_essai_id=self.conflict_essai_id
        
        keys=['Work_ID','Essai_ID']
        values=[org_work_id,conflict_essai_id]
        
        l=convert_key_value(keys,values)
            
        condition=convert_and_condition(l)
        
        # 将原来的通讯作者改为非通讯作者
        keys=['Is_Comm_Author']
        values=[0]
        db=self.db
        table=self.table # 注意这里table应当恒为'Publish'
        
        pairs=convert_key_value(keys,values)
        pair=''
        first=1
        for e in pairs:
            if not first:
                pair+=','
            else:
                first=0
            pair+=e
        command='update '+table+' set '+pair+' where '+condition
        
        db_update_command(db,command,0)
        
        # 触发该特殊处理的操作应当自行完成对新通讯作者的标识
    
    # 查找同排名承担者，以避免出现承担者相同排名的情况
    # 注意在批量更新时，应当同时检查排名情况
    def select_res_rank(self):
        keys=['Project_ID','Undertake_Sequence']
        values=[self.current_project_id,self.current_rank]
        
        l=convert_key_value(keys,values)
            
        condition=convert_and_condition(l)
        
        db=self.db
        table=self.table # 注意这里table应当恒为'Undertake'
        
        n,l=select(db,table,condition)
        
        return n,l
    
    # 查找总项目经费，在每次保存时，应当检查一个项目列表中的所有项目的被承担经费总和
    def select_project_funding(self):
        keys=['Project_ID']
        values=[self.current_project_id]
        
        l=convert_key_value(keys,values)
            
        condition=convert_and_condition(l)
        
        db=self.db
        table='Undertake' # 注意这里table应当为'Undertake'，但一般调用函数时不能保证这一点
        
        n,l=select(db,table,condition)
        
        return n,l

    def select_total_funding(self):
        keys=['Project_ID']
        values=[self.current_project_id]
        
        l=convert_key_value(keys,values)
            
        condition=convert_and_condition(l)
        
        db=self.db
        table='Project' # 注意这里table应当为'Project'，但一般调用函数时不能保证这一点
        
        n,l=select(db,table,condition)
        
        return n,l
    
    # 更新总项目经费：用户应当可以选择根据实际计算出的值重新定义总经费数额
    def change_total_funding(self):
        project_id=self.current_project_id
        total_funding=self.current_total_funding
        
        keys=['Project_ID']
        values=[project_id]
        
        l=convert_key_value(keys,values)
            
        condition=convert_and_condition(l)
        
        # 重新设定总经费数额
        keys=['Total_Funding']
        values=[total_funding]
        db=self.db
        table='Project' # 注意这里table应当为'Project'，但一般调用函数时不能保证这一点
        
        pairs=convert_key_value(keys,values)
        pair=''
        first=1
        for e in pairs:
            if not first:
                pair+=','
            else:
                first=0
            pair+=e
        command='update '+table+' set '+pair+' where '+condition
        
        db_update_command(db,command,0)
        
    # 执行课时数的检查时，应当注意课程与学期、学年的独立性
    # 查找总课时数
    def select_course_hour(self):
        keys=['Course_ID','Course_Year','Semester']
        values=[self.current_course_id,self.current_course_year,self.current_semester]
        
        l=convert_key_value(keys,values)
            
        condition=convert_and_condition(l)
        
        db=self.db
        table='Teach'
        
        n,l=select(db,table,condition)
        
        return n,l

    def select_total_hour(self):
        keys=['Course_ID']
        values=[self.current_course_id]
        
        l=convert_key_value(keys,values)
            
        condition=convert_and_condition(l)
        
        db=self.db
        table='Course'
        
        n,l=select(db,table,condition)
        
        return n,l
    
    # 更新总课时数（当不同次课程出现总课时数不一致的情况时，应当报错）
    def change_total_hour(self):
        course_id=self.current_course_id
        total_hour=self.current_total_hour
        
        keys=['Course_ID']
        values=[course_id]
        
        l=convert_key_value(keys,values)
            
        condition=convert_and_condition(l)
        
        keys=['Course_Hour']
        values=[total_hour]
        db=self.db
        table='Course'
        
        pairs=convert_key_value(keys,values)
        pair=''
        first=1
        for e in pairs:
            if not first:
                pair+=','
            else:
                first=0
            pair+=e
        command='update '+table+' set '+pair+' where '+condition
        
        db_update_command(db,command,0)
        
    # 特殊功能：输出对单个教授，返回其特定年份范围的学术活动
    def output_all(self):
        db=self.db
        table='Professor'
        condition=self.current_condition
        
        n,l=select(db,table,condition)
        
        self.output_year_list=range(self.year_f,self.year_t+1)
        
        for e in l:
            self.current_work_id=e[key_dict[table].index('Work_ID')]
            self.output_activities()
    
    def output_activities(self):
        work_id=self.current_work_id
        
        keys=['Work_ID']
        values=[work_id]
        
        l=convert_key_value(keys,values)
            
        condition=convert_and_condition(l)
        
        db=self.db
        
        now=datetime.now()
        self.workbook=xlsxwriter.Workbook(work_id+'_'+now.strftime("%Y%m%d%H%M%S")+'.xlsx')
        
        noutput=0
        tooutput=[]
        
        table='Publish'
        n,l=select(db,table,condition)
        for e in l:
            aug_keys=['Essai_ID']
            aug_values=[e[key_dict[table].index('Essai_ID')]]
            aug_l=convert_key_value(aug_keys,aug_values)
            aug_condition=convert_and_condition(aug_l)
            _,raw_essai=select(db,'Essai',aug_condition)
            essai=raw_essai[0]
            
            date=essai[key_dict['Essai'].index('Publish_Date')]
            year=date.year
            if year in self.output_year_list:
                tooutput.append(e)
                noutput+=1
        self.worksheet=self.workbook.add_worksheet('发表论文情况')
        self.complete_sheet(table,noutput,tooutput)
        
        noutput=0
        tooutput=[]
        
        table='Undertake'
        n,l=select(db,table,condition)
        for e in l:
            aug_keys=['Project_ID']
            aug_values=[e[key_dict[table].index('Project_ID')]]
            aug_l=convert_key_value(aug_keys,aug_values)
            aug_condition=convert_and_condition(aug_l)
            _,raw_project=select(db,'Project',aug_condition)
            project=raw_project[0]
            
            start_date=project[key_dict['Project'].index('Start_Date')]
            finish_date=project[key_dict['Project'].index('Finish_Date')]
            start_year=start_date.year
            finish_year=finish_date.year
            if len([value for value in list(self.output_year_list) if value in list(range(start_year,finish_year+1))])>0:
                tooutput.append(e)
                noutput+=1
        self.worksheet=self.workbook.add_worksheet('参与项目情况')
        self.complete_sheet(table,noutput,tooutput)
        
        noutput=0
        tooutput=[]
        
        table='Teach'
        n,l=select(db,table,condition)
        for e in l:
            year=e[key_dict[table].index('Course_Year')]
            if year in self.output_year_list:
                tooutput.append(e)
                noutput+=1
        self.worksheet=self.workbook.add_worksheet('讲授课程情况')
        self.complete_sheet(table,noutput,tooutput)
        
        self.workbook.close()
        
    def complete_sheet(self,table,n,l):
        if n==0:
            self.worksheet.write(0,0,'该教授在给定时间内没有相关学术活动。')
        else:
            for e in key_dict[table]:
                idx=key_dict[table].index(e)
                self.worksheet.write(0,idx,e)
            for e in l:
                translated=translate_list(e,table)
                idxl=l.index(e)
                for a in translated:
                    idxe=translated.index(a)
                    self.worksheet.write(idxl+1,idxe,a)
    
    # condition需要被保存，因为它仍然会被更新/删除命令用到
    # 仍然需要output_table组件处在layout中
    """def UI_select(self):
        db=self.db
        table=self.table
        condition=self.condition
        
        n,l=select(db,table,condition)
        
        self.output_table.setRowCount(n)
        self.output_table.setColumnCount(len(key_dict_cn[table]))
        self.output_table.setHorizontalHeaderLabels(key_dict_cn[table])
        
        for i in range(n):
            for j in range(len(key_dict_cn[table])):
                item=QTableWidgetItem(str(l[i][j]))
                self.output_table.setItem(i,j,item)"""
                
    # 由于在更新/删除前都会进行查找，因此不会出现没有目标的情况
    # 可以增加一组信息窗口进行对用户的提示
    # keys可以通过字典查询确定，values可以在别的方法中保存
    # 默认不直接保存，而是设置统一保存的按钮
    def UI_action(self):
        db=self.db
        table=self.table
        
        if self.operation=='select':
            condition=self.condition
            self.current_condition=self.condition
            
            n,l=select(db,table,condition)
            
            self.have_result=(n>0)
            
            self.output_table.setRowCount(n)
            self.output_table.setColumnCount(len(key_dict_cn[table]))
            self.output_table.setHorizontalHeaderLabels(key_dict_cn[table])
            
            for i in range(n):
                translated=translate_list(l[i],table)
                # print(l[i])
                # print(translated)
                for j in range(len(key_dict_cn[table])):
                    item=QTableWidgetItem(str(translated[j]))
                    self.output_table.setItem(i,j,item)
        
        elif self.operation=='insert':
            keys=key_dict[table]
            values=self.values
            
            str_keys=convert_key(keys)
            str_values=convert_value(values)
            command='insert into '+table+' ('+str_keys+') values ('+str_values+')'
            db_update_command(db,command,0)
            
        elif self.operation=='delete':
            condition=self.condition
            
            if condition!='':
                command='delete from '+table+' where '+condition
            else:
                command='delete from '+table
            db_update_command(db,command,0)
            
        elif self.operation=='update':
            keys=self.keys
            values=self.values
            condition=self.condition
            
            pairs=convert_key_value(keys,values)
            pair=''
            first=1
            for e in pairs:
                if not first:
                    pair+=','
                else:
                    first=0
                pair+=e
            if condition!='':
                command='update '+table+' set '+pair+' where '+condition
            else:
                command='update '+table+' set '+pair
            db_update_command(db,command,0)
    
    # 封装各类基本功能的测试
    def test1_UI_select(self):
        self.table='Course'
        self.output_table=QTableWidget()
        self.layout=QGridLayout()
        self.layout.addWidget(self.output_table,0,0)
        self.UI_select()
        self.setLayout(self.layout)
        
    def test2_UI_select_after_update(self):
        cursor=self.db.cursor()
        cursor.execute("insert into Course (Course_ID,Course_Name,Course_Hour,Course_Type) values ('CMATH','MATH',1000,2)")
        self.table='Course'
        self.output_table=QTableWidget()
        self.layout=QGridLayout()
        self.layout.addWidget(self.output_table,0,0)
        self.UI_select()
        self.setLayout(self.layout)
        
    def test3_UI_insert(self):
        self.operation='insert'
        self.table='Course'
        self.values=['CMATH','ALGEBRA',1000,2]
        self.condition=''
        self.output_table=QTableWidget()
        self.layout=QGridLayout()
        self.layout.addWidget(self.output_table,0,0)
        self.UI_update()
        self.UI_select()
        self.setLayout(self.layout)
        
    def test4_UI_delete(self):
        self.operation='delete'
        self.table='Course'
        self.condition='Course_Type=2'
        self.output_table=QTableWidget()
        self.layout=QGridLayout()
        self.layout.addWidget(self.output_table,0,0)
        self.UI_update()
        self.condition=''
        self.UI_select()
        self.setLayout(self.layout)
        
    def test5_UI_update(self):
        self.operation='update'
        self.table='Course'
        self.keys=['Course_Hour','Course_Type']
        self.values=[1000,1]
        self.condition='Course_Type=2'
        self.output_table=QTableWidget()
        self.layout=QGridLayout()
        self.layout.addWidget(self.output_table,0,0)
        self.UI_update()
        self.condition=''
        self.UI_select()
        self.setLayout(self.layout)

# 将数据库内容转化为有意义的信息
def translate_list(l,table):
    ret=[]
    if table=='Professor':
        ret.append(l[0])
        ret.append(l[1])
        if isinstance(l[2],int):
            ret.append(genders[l[2]-1])
        else:
            ret.append(l[2])
        if isinstance(l[3],int):
            ret.append(titles[l[3]-1])
        else:
            ret.append(l[3])
    elif table=='Essai':
        ret.append(l[0])
        ret.append(l[1])
        ret.append(l[2])
        ret.append(l[3])
        if isinstance(l[4],int):
            ret.append(essai_type[l[4]-1])
        else:
            ret.append(l[4])
        if isinstance(l[5],int):
            ret.append(essai_rank[l[5]-1])
        else:
            ret.append(l[5])
    elif table=='Project':
        ret.append(l[0])
        ret.append(l[1])
        ret.append(l[2])
        if isinstance(l[3],int):
            ret.append(project_type[l[3]-1])
        else:
            ret.append(l[3])
        ret.append(l[4])
        ret.append(l[5])
        ret.append(l[6])
    elif table=='Course':
        ret.append(l[0])
        ret.append(l[1])
        ret.append(l[2])
        if isinstance(l[3],int):
            ret.append(course_type[l[3]-1])
        else:
            ret.append(l[3])
    elif table=='Publish':
        ret.append(l[0])
        ret.append(l[1])
        ret.append(l[2])
        ret.append('是' if l[3] else '否')
    elif table=='Undertake':
        ret.append(l[0])
        ret.append(l[1])
        ret.append(l[2])
        ret.append(l[3])
    elif table=='Teach':
        ret.append(l[0])
        ret.append(l[1])
        ret.append(l[2])
        if isinstance(l[3],int):
            ret.append(semesters[l[3]-1])
        else:
            ret.append(l[3])
        ret.append(l[4])
    return ret

# UI方法用来封装各类返回和报错信息
def UI_success():
    print('Operation successful!')
    
def UI_system_error():
    print('In-program error occurred!')
    
def UI_connection_error():
    print('Connection failed!')
    
def is_alphabet_number(s):
    for e in s:
        if not (e>='A' and e<='Z' or e>='a' and e<='z' or e>='0' and e<='9'):
            return False
    return True
    
def convert_key(l):
    # 将一组数据转化为字符串，用于面向数据库的输入。
    # 保证只有字符串输入。
    ret=''
    first=1
    for e in l:
        if not first:
            ret+=', '
        else:
            first=0
        ret+=e
    return ret

def convert_value(l):
    # 将一组数据转化为字符串，用于面向数据库的输入。
    # 保证只有三类数据被输入：整数，浮点数和字符串。通过在用户输入时进行检测来保证这一点。
    ret=''
    first=1
    for e in l:
        if not first:
            ret+=', '
        else:
            first=0
        if isinstance(e,int):
            ret+=str(e)
        if isinstance(e,float):
            ret+=str(e)
        if isinstance(e,str):
            if e!='None':
                ret+='\''+e+'\''
            else:
                ret+='null'
    return ret

def convert_and_condition(l):
    # 将一组条件转化为字符串，用于对数据库内容进行条件判断。
    ret=''
    first=1
    for e in l:
        if not first:
            ret+=' and '
        else:
            first=0
        ret+=e
    return ret

def convert_or_condition(l):
    # 将一组条件转化为字符串，用于对数据库内容进行条件判断。
    ret='('
    first=1
    for e in l:
        if not first:
            ret+=' or '
        else:
            first=0
        ret+=e
    ret+=')'
    return ret

def convert_key_value(key,value):
    # 将一组键值对转化为字符串，用于对数据库内容的更新和查找。
    ret=[]
    for i in range(len(key)):
        if not (isinstance(value[i],str)):
            ret.append(key[i]+'='+str(value[i]))
        elif value[i]!='None':
            ret.append(key[i]+'=\''+str(value[i])+'\'')
    return ret

def db_connect():
    # 连接数据库
    try:
        config=ConfigParser()
        config.read("config.cfg")
        section=config.sections()[0]

        host=config.get(section,"host")
        user=config.get(section,"user")
        passwd=config.get(section,"passwd")
        port=config.getint(section,"port")
        
        db=pymysql.connect(host=host,user=user,passwd=passwd,port=port)
        
        cursor=db.cursor()
        cursor.execute('use lab3')
        
        UI_success()

        return db
    except:
        UI_connection_error()
        return None

def db_update_command(db,command,if_commit):
    # 数据库更新命令
    # print(command)
    cursor=db.cursor()
    cursor.execute(command)
    if if_commit:
        db.commit()
    UI_success()
    """try:
        cursor.execute(command)
        if if_commit:
            db.commit()
        UI_success()
    except:
        db.rollback()
        UI_system_error()"""

def db_select_command(db,command):
    # 数据库查找命令
    # print(command)
    cursor=db.cursor()
    ret=cursor.execute(command)
    UI_success()
    return ret,cursor.fetchall()
    """try:
        ret=cursor.execute(command)
        UI_success()
        return ret,cursor.fetchall()
    except:
        db.rollback()
        UI_system_error()
        return -1,None"""

def has_foreign_key(table):
    # 判断给定的表是否依赖外键
    return table in foreign_table_dict.keys()

def insert(db,table,keys,values,if_commit):
    str_keys=convert_key(keys)
    str_values=convert_value(values)
    command='insert into '+table+' ('+str_keys+') values ('+str_values+')'
    db_update_command(db,command,if_commit)
    
def remove(db,table,condition,if_commit):
    command='delete from '+table+' where '+condition
    db_update_command(db,command,if_commit)
    
def update(db,table,condition,keys,values,if_commit):
    pair=convert_key_value(keys,values)
    command='update '+table+' set '+pair+' where '+condition
    db_update_command(db,command,if_commit)
    
def select(db,table,condition):
    if condition=='':
        command='select * from '+table
    else:
        command='select * from '+table+' where '+condition
    n,l=db_select_command(db,command)
    return n,l
    
def insert_into_basic_table(db,table,values,if_commit):
    insert(db,table,key_dict[table],values,if_commit)
    
def insert_into_constrainted_table(db,table,values,if_commit):
    # 找到对应外键的表
    # 利用了已知信息：每个外键对应不同的表，且一个外键只在一个表中出现一次
    foreign_tables=foreign_table_dict[table]
    eligible=True
    availibility=[]
    foreign_info=[]
    for e in foreign_tables:
        pk_list=primary_key_dict[e]
        select_keys=[]
        select_values=[]
        for pk in pk_list:
            pk_value=values[key_dict[table].index(pk)]
            select_keys.append(pk)
            select_values.append(pk_value)
        condition_list=convert_key_value(select_keys,select_values)
        condition=convert_and_condition(condition_list)
        n,l=select(db,e,condition)
        availibility.append((n>0))
        # 这里应当一次只新增一个元素，因为根据题目的描述，外键都是所在的表的主键
        foreign_info.append(l)
        if n==0:
            eligible=False
    # print(availibility)
    # print(foreign_info)
    if eligible:
        insert(db,table,key_dict[table],values,if_commit)

app = QApplication(sys.argv)
ui=PyQtUI()
ui.show()
sys.exit(app.exec())