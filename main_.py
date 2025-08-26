import streamlit as st
import pandas as pd
import os
from datetime import date, datetime
from PIL import Image
import numpy as np
import cv2
import qrcode
from io import BytesIO
import time
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials

class StudentAttendanceSystem:
    def __init__(self):
        st.set_page_config(page_title="نظام حضور الطلاب", layout="wide", page_icon="🎓")
        
        # تعريف أسماء الأشهر الجديدة
        self.months = [
            'يوليو_2025', 'أغسطس_2025', 'سبتمبر_2025', 'أكتوبر_2025', 
            'نوفمبر_2025', 'ديسمبر_2025', 'يناير_2026', 'فبراير_2026', 
            'مارس_2026', 'أبريل_2026', 'مايو_2026', 'يونيو_2026'
        ]
        
        # تهيئة اتصال Google Sheets
        self.init_google_sheets()
        self.current_group = "المجموعة_الافتراضية"
        # تحميل البيانات أولاً قبل إعداد الواجهة
        self.load_data()
        self.setup_ui()
    
    def init_google_sheets(self):
        """تهيئة اتصال Google Sheets"""
        try:
            # تحديد الـ scope
            scope = ["https://spreadsheets.google.com/feeds",
                    "https://www.googleapis.com/auth/drive",
                    "https://www.googleapis.com/auth/spreadsheets"]
            
            # تحميل credentials (يجب تعديل المسار ليتناسب مع نظامك)
            creds_path = r"C:\Users\zbook 17 g3\Desktop\chromatic-theme-470014-a7-1dcc78299d05.json"
            
            if os.path.exists(creds_path):
                creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
                self.client = gspread.authorize(creds)
                
                # ID الشيت من الرابط
                self.SHEET_ID = "1tna1xqoBN3WBv7LJvCblyGUrozcA2FkMvk-VoT6UHic"
                
                # فتح الشيت الرئيسي
                try:
                    self.spreadsheet = self.client.open_by_key(self.SHEET_ID)
                except gspread.SpreadsheetNotFound:
                    st.error("لم يتم العثور على جدول البيانات. تأكد من ID الصحيح.")
                    return
                
                print("تم الاتصال بـ Google Sheets بنجاح")
            else:
                st.error("ملف الاعتماد غير موجود. تأكد من المسار الصحيح.")
                
        except Exception as e:
            st.error(f"خطأ في الاتصال بـ Google Sheets: {str(e)}")
    
    def load_data(self):
        """تحميل البيانات من Google Sheets"""
        try:
            # الحصول على قائمة بأسماء الأوراق (المجموعات)
            try:
                worksheets = self.spreadsheet.worksheets()
                sheet_names = [ws.title for ws in worksheets]
            except:
                sheet_names = []
            
            self.groups_df = {}
            
            if sheet_names:
                for sheet_name in sheet_names:
                    try:
                        worksheet = self.spreadsheet.worksheet(sheet_name)
                        records = worksheet.get_all_records()
                        
                        if records:
                            df = pd.DataFrame(records)
                            
                            # تصحيح الأعمدة إذا كان هناك خطأ إملائي
                            
                            
                            # إضافة الأعمدة المفقودة
                            required_columns = [
                                'الكود', 'الاسم', 'رقم_الهاتف', 'ولي_الامر', 'الحصص_الحاضرة'
                            ] + self.months + [
                                'تواريخ_الحضور', 'تاريخ_التسجيل', 'ملاحظات', 'الاختبارات'
                            ]
                            
                            for col in required_columns:
                                if col not in df.columns:
                                    if col in self.months:
                                        df[col] = False
                                    elif col == 'الحصص_الحاضرة':
                                        df[col] = 0
                                    else:
                                        df[col] = ''
                            
                            # تحويل أنواع البيانات
                            df['الكود'] = df['الكود'].astype(str)
                            df['الاسم'] = df['الاسم'].astype(str)
                            df['رقم_الهاتف'] = df['رقم_الهاتف'].astype(str)
                            df['ولي_الامر'] = df['ولي_الامر'].astype(str)
                            df['الحصص_الحاضرة'] = pd.to_numeric(df['الحصص_الحاضرة'], errors='coerce').fillna(0).astype(int)
                            df['تواريخ_الحضور'] = df['تواريخ_الحضور'].astype(str).fillna('')
                            df['ملاحظات'] = df['ملاحظات'].astype(str).fillna('')
                            df['الاختبارات'] = df['الاختبارات'].astype(str).fillna('')
                            
                            # معالجة تاريخ التسجيل
                            try:
                                df['تاريخ_التسجيل'] = pd.to_datetime(df['تاريخ_التسجيل'], errors='coerce').dt.date
                                df['تاريخ_التسجيل'] = df['تاريخ_التسجيل'].fillna(date.today())
                            except:
                                df['تاريخ_التسجيل'] = date.today()
                            
                            # التأكد من أن أعمدة الأشهر من النوع المنطقي
                            for month in self.months:
                                df[month] = df[month].astype(bool)
                            
                            self.groups_df[sheet_name] = df
                        else:
                            # إنشاء DataFrame فارغ إذا كانت الورقة فارغة
                            required_columns = [
                                'الكود', 'الاسم', 'رقم_الهاتف', 'ولي_الامر', 'الحصص_الحاضرة'
                            ] + self.months + [
                                'تواريخ_الحضور', 'تاريخ_التسجيل', 'ملاحظات', 'الاختبارات'
                            ]
                            self.groups_df[sheet_name] = pd.DataFrame(columns=required_columns)
                            
                    except Exception as e:
                        print(f"خطأ في تحميل ورقة {sheet_name}: {str(e)}")
                        continue
            
            # إذا لم توجد أوراق، إنشاء مجموعة افتراضية
            if not self.groups_df:
                self.initialize_default_group()
            else:
                # تحديد المجموعة الحالية
                if self.current_group is None or self.current_group not in self.groups_df:
                    self.current_group = list(self.groups_df.keys())[0]
                
                print(f"تم تحميل البيانات بنجاح. عدد المجموعات: {len(self.groups_df)}")
                
        except Exception as e:
            print(f"حدث خطأ في تحميل البيانات: {str(e)}")
            st.error(f"حدث خطأ في تحميل البيانات: {str(e)}")
            self.initialize_default_group()

    def initialize_default_group(self):
        """إنشاء مجموعة افتراضية جديدة"""
        required_columns = [
            'الكود', 'الاسم', 'رقم_الهاتف', 'ولي_الامر', 'الحصص_الحاضرة'
        ] + self.months + [
            'تواريخ_الحضور', 'تاريخ_التسجيل', 'ملاحظات', 'الاختبارات'
        ]
        
        self.groups_df = {
            "المجموعة_الافتراضية": pd.DataFrame(columns=required_columns)
        }
        self.current_group = "المجموعة_الافتراضية"
        
        # حفظ الملف فوراً
        self.save_data()
        print("تم إنشاء مجموعة افتراضية جديدة")
    
    def save_data(self):
        """حفظ البيانات في Google Sheets"""
        try:
            # الحصول على الأوراق الحالية
            current_sheets = self.spreadsheet.worksheets()
            current_sheet_names = [ws.title for ws in current_sheets]
            
            for group_name, df in self.groups_df.items():
                # إنشاء نسخة للحفظ
                df_to_save = df.copy()
                
                # تحويل التواريخ لنص للحفظ
                if 'تاريخ_التسجيل' in df_to_save.columns:
                    df_to_save['تاريخ_التسجيل'] = df_to_save['تاريخ_التسجيل'].astype(str)
                
                # استبدال القيم الفارغة بنصوص فارغة
                df_to_save = df_to_save.fillna('')
                
                # تحويل DataFrame إلى قائمة من القوائم
                data_to_save = [df_to_save.columns.tolist()] + df_to_save.values.tolist()
                
                # التحقق إذا كانت الورقة موجودة
                if group_name in current_sheet_names:
                    worksheet = self.spreadsheet.worksheet(group_name)
                    # مسح الورقة الحالية
                    worksheet.clear()
                else:
                    # إنشاء ورقة جديدة
                    worksheet = self.spreadsheet.add_worksheet(title=group_name, rows=1000, cols=20)
                
                # تحديث البيانات
                worksheet.update('A1', data_to_save)
                
                print(f"تم حفظ بيانات المجموعة {group_name} بنجاح")
            
            print("تم حفظ جميع البيانات بنجاح في Google Sheets")
            
        except Exception as e:
            print(f"خطأ في حفظ البيانات: {str(e)}")
            st.error(f"خطأ في حفظ البيانات: {str(e)}")
    
    def setup_ui(self):
        # ... (نفس كود setup_ui السابق بدون تغيير)
        st.markdown("""
        <style>
            .stApp {
                background-color: #0E1117;
                color: #FAFAFA;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #FFFFFF !important;
            }
            .stTextInput>div>div>input, 
            .stTextArea>div>div>textarea, 
            .stSelectbox>div>div>select,
            .stNumberInput>div>div>input {
                color: #FFFFFF;
                background-color: #1E1E1E;
            }
            .stats-card {
                background: linear-gradient(135deg, #1E1E1E, #2A2A2A);
                border-radius: 10px;
                padding: 15px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
                text-align: center;
                border-left: 4px solid #4CAF50;
            }
            .stDownloadButton>button {
                background-color: #4CAF50 !important;
                color: white !important;
                border: none;
                font-weight: bold;
            }
            .welcome-message {
                font-size: 42px !important;
                font-weight: bold !important;
                color: #4CAF50 !important;
                text-align: center;
                margin: 20px 0;
                text-shadow: 2px 2px 4px #000;
            }
            .stButton>button {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                border: none;
            }
            .stTabs [role="tablist"] {
                background: #1E1E1E;
            }
            .dataframe {
                background-color: #1E1E1E !important;
                color: white !important;
            }
            .student-info {
                background-color: #1E1E1E;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            }
            .save-status {
                position: fixed;
                top: 10px;
                right: 10px;
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border-radius: 5px;
                z-index: 1000;
            }
        </style>
        """, unsafe_allow_html=True)
        
        st.title("🎓 نظام حضور الطلاب")
        
        # عرض حالة آخر حفظ
        st.info("📁 البيانات متصلة بـ Google Sheets - يتم الحفظ تلقائياً")
        
        # إدارة المجموعات في الشريط الجانبي
        with st.sidebar:
            st.header("إدارة المجموعات")
            
            # عرض المجموعات الحالية
            current_groups = list(self.groups_df.keys())
            self.current_group = st.selectbox(
                "اختر المجموعة الحالية", 
                current_groups, 
                index=current_groups.index(self.current_group) if self.current_group in current_groups else 0
            )
            
            # إضافة مجموعة جديدة
            new_group_name = st.text_input("اسم المجموعة الجديدة")
            if st.button("➕ إضافة مجموعة") and new_group_name:
                if new_group_name not in self.groups_df:
                    required_columns = [
                        'الكود', 'الاسم', 'رقم_الهاتف', 'ولي_الامر', 'الحصص_الحاضرة'
                    ] + self.months + [
                        'تواريخ_الحضور', 'تاريخ_التسجيل', 'ملاحظات', 'الاختبارات'
                    ]
                    
                    self.groups_df[new_group_name] = pd.DataFrame(columns=required_columns)
                    self.save_data()
                    st.success(f"تم إنشاء المجموعة '{new_group_name}' بنجاح!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("هذه المجموعة موجودة بالفعل!")
            
            # حذف مجموعة
            if len(self.groups_df) > 1:
                group_to_delete = st.selectbox("اختر مجموعة للحذف", current_groups)
                if st.button("🗑️ حذف المجموعة") and group_to_delete:
                    try:
                        # حذف الورقة من Google Sheets
                        worksheet = self.spreadsheet.worksheet(group_to_delete)
                        self.spreadsheet.del_worksheet(worksheet)
                        
                        # حذف من البيانات المحلية
                        del self.groups_df[group_to_delete]
                        self.current_group = list(self.groups_df.keys())[0]
                        
                        st.success(f"تم حذف المجموعة '{group_to_delete}' بنجاح!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطأ في حذف المجموعة: {str(e)}")
            
            # زر حفظ يدوي
            if st.button("💾 حفظ البيانات يدوياً"):
                self.save_data()
                st.success("تم حفظ البيانات!")
        
        # تبويبات الواجهة الرئيسية
        tabs = st.tabs(["📷 مسح حضور الطالب", "➕ تسجيل طالب جديد", "🔄 إدارة الطلاب", "📊 الإحصائيات"])
        
        with tabs[0]:
            self.scan_qr_tab()
        with tabs[1]:
            self.create_student_tab()
        with tabs[2]:
            self.manage_students_tab()
        with tabs[3]:
            self.view_analytics_tab()
    
    # ... (بقية الدوال تبقى كما هي بدون تغيير)
    def scan_qr_tab(self):
        if self.current_group not in self.groups_df:
            st.warning("الرجاء اختيار مجموعة صالحة")
            return
            
        st.header(f"📷 تسجيل حضور الطالب - مجموعة {self.current_group}")
        welcome_placeholder = st.empty()
        
        # استخدام session state لتجنب المعالجة المكررة للصورة
        if 'last_processed_image' not in st.session_state:
            st.session_state.last_processed_image = None
        
        img_file = st.camera_input("امسح كود الطالب", key="qr_scanner")
        
        # إذا كانت هناك صورة جديدة ولم يتم معالجتها من قبل
        if img_file is not None and img_file != st.session_state.last_processed_image:
            st.session_state.last_processed_image = img_file
            
            try:
                img = Image.open(img_file)
                frame = np.array(img)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                detector = cv2.QRCodeDetector()
                data, vertices, _ = detector.detectAndDecode(gray)
                
                if data:
                    self.process_student_attendance(data.strip(), welcome_placeholder)
                else:
                    st.warning("لم يتم التعرف على كود الطالب، حاول مرة أخرى")
            except Exception as e:
                st.error(f"خطأ في المسح: {str(e)}")
        
        # زر لمسح الصورة يدوياً إذا احتجنا
        if st.button("🗑️ مسح الصورة والبدء من جديد"):
            st.session_state.last_processed_image = None
            st.rerun()
    
    def process_student_attendance(self, student_id, welcome_placeholder):
        # البحث عن الطالب في جميع المجموعات
        student_found = False
        student_group = None
        student_row = None
        student_index = None
        
        for group_name, df in self.groups_df.items():
            if student_id in df['الكود'].values:
                student_found = True
                student_group = group_name
                student_index = df[df['الكود'] == student_id].index[0]
                student_row = df.loc[student_index]
                break
        
        if student_found:
            # التحقق من عدم تكرار تسجيل الحضور لنفس الصورة
            if f'last_attendance_{student_id}' not in st.session_state:
                st.session_state[f'last_attendance_{student_id}'] = None
            
            if st.session_state[f'last_attendance_{student_id}'] != st.session_state.last_processed_image:
                # تحديث عدد الحصص
                self.groups_df[student_group].loc[student_index, 'الحصص_الحاضرة'] += 1
                
                # تسجيل تاريخ الحضور
                current_date = date.today().strftime("%Y-%m-%d")
                current_presence = student_row['تواريخ_الحضور']
                
                if pd.isna(current_presence) or current_presence == '' or current_presence == 'nan':
                    new_presence = current_date
                else:
                    new_presence = f"{current_presence}; {current_date}"
                    
                self.groups_df[student_group].loc[student_index, 'تواريخ_الحضور'] = new_presence
                
                # حفظ البيانات فوراً
                self.save_data()
                
                # تسجيل أن هذه الصورة تم معالجتها
                st.session_state[f'last_attendance_{student_id}'] = st.session_state.last_processed_image
                
                print(f"تم تسجيل حضور للطالب {student_id} في المجموعة {student_group}")
            
            # إعادة قراءة البيانات المحدثة
            updated_student_row = self.groups_df[student_group].loc[student_index]
            
            # عرض معلومات الطالب
            welcome_html = f"""
            <div class='welcome-message'>
                <div style='font-size: 48px;'>مرحباً</div>
                <div style='font-size: 56px;'>{updated_student_row['الاسم']}</div>
                <div style='font-size: 24px; margin-top: 20px;'>
                    المجموعة: <span style='color: #FFD700;'>{student_group}</span><br>
                    الحصص الحاضرة: <span style='color: #FFD700;'>{int(updated_student_row['الحصص_الحاضرة'])}</span>
                </div>
            </div>
            """
            welcome_placeholder.markdown(welcome_html, unsafe_allow_html=True)
            
            # عرض تفاصيل الطالب
            st.markdown('<div class="student-info">', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### المعلومات الشخصية")
                st.markdown(f"""
                - **المجموعة**: {student_group}
                - **الكود**: {updated_student_row['الكود']}
                - **الاسم**: {updated_student_row['الاسم']}
                - **رقم الهاتف**: {updated_student_row['رقم_الهاتف']}
                - **ولي الأمر**: {updated_student_row['ولي_الامر']}
                - **تاريخ التسجيل**: {updated_student_row['تاريخ_التسجيل']}
                """)
                
            with col2:
                st.markdown("### الحضور والدفع")
                months_paid = [month for month in self.months if updated_student_row[month]]
                months_display = [month.replace('_', ' ') for month in months_paid]
                
                st.markdown(f"""
                - **الحصص الحاضرة**: {int(updated_student_row['الحصص_الحاضرة'])}
                - **الأشهر المدفوعة**: {', '.join(months_display) if months_paid else 'لا يوجد'}
                """)
            
            # عرض تواريخ الحضور
            if pd.notna(updated_student_row['تواريخ_الحضور']) and updated_student_row['تواريخ_الحضور'] != '' and updated_student_row['تواريخ_الحضور'] != 'nan':
                st.markdown("### تواريخ الحضور")
                dates = str(updated_student_row['تواريخ_الحضور']).split(';')
                st.markdown('<div class="attendance-dates">', unsafe_allow_html=True)
                for i, date_str in enumerate(dates, 1):
                    date_str = date_str.strip()
                    if date_str and date_str != 'nan':
                        st.markdown(f"- الحصة {i}: {date_str}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # عرض نتائج الاختبارات
            if pd.notna(updated_student_row['الاختبارات']) and updated_student_row['الاختبارات'] != '' and updated_student_row['الاختبارات'] != 'nan':
                st.markdown("### نتائج الاختبارات")
                tests = str(updated_student_row['الاختبارات']).split(';')
                for test in tests:
                    test = test.strip()
                    if test and test != 'nan':
                        st.markdown(f"- {test}")
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            welcome_placeholder.error("❌ كود الطالب غير مسجل في النظام")
    
    def create_student_tab(self):
        st.header(f"➕ تسجيل طالب جديد")
        
        with st.form("student_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                student_name = st.text_input("اسم الطالب بالكامل", placeholder="أدخل الاسم ثلاثي")
                student_id = st.text_input("كود الطالب", placeholder="رقم فريد لكل طالب")
                phone = st.text_input("رقم هاتف الطالب", placeholder="01012345678")
                # اختيار المجموعة
                group_options = list(self.groups_df.keys())
                selected_group = st.selectbox("اختر المجموعة", group_options)
            
            with col2:
                parent_phone = st.text_input("رقم ولي الأمر", placeholder="01012345678")
                registration_date = st.date_input("تاريخ التسجيل", value=date.today())
                notes = st.text_area("ملاحظات إضافية")
            
            # تحديد الشهر الحالي بناءً على تاريخ التسجيل
            current_month = None
            if registration_date:
                month_num = registration_date.month
                year = registration_date.year
                
                months_mapping = {
                    7: 'يوليو_2025', 8: 'أغسطس_2025', 9: 'سبتمبر_2025', 
                    10: 'أكتوبر_2025', 11: 'نوفمبر_2025', 12: 'ديسمبر_2025',
                    1: 'يناير_2026', 2: 'فبراير_2026', 3: 'مارس_2026', 
                    4: 'أبريل_2026', 5: 'مايو_2026', 6: 'يونيو_2026'
                }
                
                current_month = months_mapping.get(month_num)
            
            # إظهار حالة الدفع
            st.subheader("حالة الدفع للأشهر")
            if current_month:
                st.info(f"سيتم تحديد شهر {current_month.replace('_', ' ')} تلقائياً كمدفوع بناءً على تاريخ التسجيل")
            
            if st.form_submit_button("تسجيل الطالب"):
                if student_name and student_id:
                    # التحقق من عدم وجود الكود في أي مجموعة
                    code_exists = False
                    for group_name, df in self.groups_df.items():
                        if student_id in df['الكود'].values:
                            code_exists = True
                            break
                    
                    if code_exists:
                        st.error("هذا الكود مسجل بالفعل لطالب آخر في إحدى المجموعات")
                    else:
                        # إنشاء حالة الدفع
                        month_status = {}
                        for month in self.months:
                            month_status[month] = (month == current_month)
                        
                        qr_image = self.create_student(
                            student_id,
                            student_name,
                            phone,
                            parent_phone,
                            registration_date,
                            notes,
                            month_status,
                            selected_group
                        )
                        
                        st.success("تم تسجيل الطالب بنجاح! ✅")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.image(qr_image, caption=f"كود الطالب {student_name}", width=300)
                        
                        with col2:
                            months_paid = [m.replace('_', ' ') for m, paid in month_status.items() if paid]
                            st.markdown(f"""
                            ### بيانات الطالب المسجل:
                            - **المجموعة**: {selected_group}
                            - **الاسم**: {student_name}
                            - **كود الطالب**: {student_id}
                            - **رقم الهاتف**: {phone}
                            - **ولي الأمر**: {parent_phone}
                            - **تاريخ التسجيل**: {registration_date}
                            - **الشهر المدفوع**: {', '.join(months_paid) if months_paid else 'لا يوجد'}
                            """)
                else:
                    st.error("الرجاء إدخال اسم الطالب وكود الطالب")
    
    def create_student(self, student_id, student_name, phone, parent_phone, registration_date, notes, month_status, group_name):
        """إنشاء طالب جديد مع حفظ فوري للبيانات"""
        try:
            # إنشاء QR Code
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(student_id)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            img_bytes = BytesIO()
            qr_img.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            
            # إعداد بيانات الطالب الجديد
            new_row_data = {
                'الكود': str(student_id),
                'الاسم': str(student_name),
                'رقم_الهاتف': str(phone),
                'ولي_الامر': str(parent_phone),
                'الحصص_الحاضرة': 0,
                'تواريخ_الحضور': '',
                'تاريخ_التسجيل': registration_date,
                'ملاحظات': str(notes) if notes else '',
                'الاختبارات': ''
            }
            
            # إضافة حالة الدفع لكل شهر
            for month in self.months:
                new_row_data[month] = month_status.get(month, False)
            
            # إضافة الطالب للمجموعة المحددة
            new_row = pd.DataFrame([new_row_data])
            
            # التأكد من ترتيب الأعمدة
            required_columns = [
                'الكود', 'الاسم', 'رقم_الهاتف', 'ولي_الامر', 'الحصص_الحاضرة'
            ] + self.months + [
                'تواريخ_الحضور', 'تاريخ_التسجيل', 'ملاحظات', 'الاختبارات'
            ]
            
            new_row = new_row[required_columns]
            
            self.groups_df[group_name] = pd.concat(
                [self.groups_df[group_name], new_row], 
                ignore_index=True
            )
            
            # حفظ البيانات فوراً
            self.save_data()
            
            print(f"تم إنشاء الطالب {student_name} بنجاح في المجموعة {group_name}")
            
            return img_bytes
            
        except Exception as e:
            print(f"خطأ في إنشاء الطالب: {str(e)}")
            st.error(f"خطأ في إنشاء الطالب: {str(e)}")
            return None
    
    def search_students(self, query, search_by="name"):
        """البحث عن الطلاب في المجموعة الحالية"""
        df = self.groups_df[self.current_group]
        
        if search_by == "name":
            # البحث بأسماء الطلاب مع الاقتراحات
            all_names = df['الاسم'].dropna().unique()
            matches = [name for name in all_names if query.lower() in str(name).lower()]
            return matches
        else:
            # البحث بأكواد الطلاب مع الاقتراحات
            all_codes = df['الكود'].dropna().unique().astype(str)
            matches = [code for code in all_codes if query.lower() in str(code).lower()]
            return matches
    
    def generate_qr_code(self, student_id):
        """إنشاء QR Code لطالب معين"""
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(student_id)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        img_bytes = BytesIO()
        qr_img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        
        return img_bytes
    
    def manage_students_tab(self):
        st.header(f"🔄 إدارة الطلاب - مجموعة {self.current_group}")
        
        df = self.groups_df[self.current_group]
        
        if not df.empty:
            # قسم البحث عن الطالب
            st.subheader("بحث عن الطالب")
            
            # خيارات البحث: بالكود أو بالاسم مع البحث الذكي
            search_option = st.radio("ابحث باستخدام:", ["الكود", "الاسم"], horizontal=True, key="manage_search")
            
            student_data = pd.DataFrame()
            
            if search_option == "الكود":
                search_query = st.text_input("اكتب كود الطالب", key="code_search_manage")
                if search_query:
                    suggestions = self.search_students(search_query, "code")
                    if suggestions:
                        selected_code = st.selectbox("الاقتراحات", suggestions, key="code_suggestions_manage")
                        student_data = df[df['الكود'] == selected_code] if selected_code else pd.DataFrame()
            else:
                search_query = st.text_input("اكتب اسم الطالب", key="name_search_manage")
                if search_query:
                    suggestions = self.search_students(search_query, "name")
                    if suggestions:
                        selected_name = st.selectbox("الاقتراحات", suggestions, key="name_suggestions_manage")
                        student_data = df[df['الاسم'] == selected_name] if selected_name else pd.DataFrame()
            
            if not student_data.empty:
                student_row = student_data.iloc[0]
                student_index = student_data.index[0]
                
                # عرض بيانات الطالب
                st.markdown('<div class="student-info">', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### المعلومات الشخصية")
                    st.markdown(f"""
                    - **الكود**: {student_row['الكود']}
                    - **الاسم**: {student_row['الاسم']}
                    - **رقم الهاتف**: {student_row['رقم_الهاتف']}
                    """)
                
                with col2:
                    st.markdown("### الحضور والدفع")
                    st.markdown(f"""
                    - **ولي الأمر**: {student_row['ولي_الامر']}
                    - **تاريخ التسجيل**: {student_row['تاريخ_التسجيل']}
                    - **الحصص الحاضرة**: {student_row['الحصص_الحاضرة']}
                    """)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # قسم إدارة الحضور والدفع والاختبارات
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["الحضور", "الدفع", "الاختبارات", "استرجاع QR Code", "حذف الطالب"])
                
                with tab1:
                    st.subheader("إدارة الحضور")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("➕ تسجيل حضور إضافي"):
                            # تحديث عدد الحصص
                            self.groups_df[self.current_group].loc[student_index, 'الحصص_الحاضرة'] += 1
                            
                            # تسجيل تاريخ الحضور
                            current_date = date.today().strftime("%Y-%m-%d")
                            current_presence = student_row['تواريخ_الحضور']
                            
                            if pd.isna(current_presence) or current_presence == '' or current_presence == 'nan':
                                new_presence = current_date
                            else:
                                new_presence = f"{current_presence}; {current_date}"
                                
                            self.groups_df[self.current_group].loc[student_index, 'تواريخ_الحضور'] = new_presence
                            
                            # حفظ البيانات فوراً
                            self.save_data()
                            st.success("تم تسجيل الحضور بنجاح!")
                            time.sleep(1)
                            st.rerun()
                    
                    with col2:
                        if st.button("➖ خصم حصة حضور"):
                            if student_row['الحصص_الحاضرة'] > 0:
                                self.groups_df[self.current_group].loc[student_index, 'الحصص_الحاضرة'] -= 1
                                
                                # إزالة آخر تاريخ حضور
                                current_presence = student_row['تواريخ_الحضور']
                                if pd.notna(current_presence) and current_presence != '' and current_presence != 'nan':
                                    dates = str(current_presence).split(';')
                                    if len(dates) > 1:
                                        new_dates = ';'.join(dates[:-1])
                                    else:
                                        new_dates = ''
                                    self.groups_df[self.current_group].loc[student_index, 'تواريخ_الحضور'] = new_dates
                                
                                # حفظ البيانات فوراً
                                self.save_data()
                                st.success("تم خصم الحصة بنجاح!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.warning("لا يمكن خصم حصة حيث أن عدد الحصص الحاضرة صفر")
                
                with tab2:
                    st.subheader("حالة الدفع للأشهر")
                    
                    # استخدام نموذج لتحديث حالة الدفع
                    with st.form(f"payment_form_{student_row['الكود']}"):
                        st.write("حدد الأشهر المدفوعة:")
                        
                        # إنشاء شبكة من الخانات لجميع الأشهر
                        cols = st.columns(4)
                        updated_payment_status = {}
                        
                        for i, month in enumerate(self.months):
                            with cols[i % 4]:
                                current_status = bool(student_row[month])
                                updated_payment_status[month] = st.checkbox(
                                    month.replace('_', ' '), 
                                    value=current_status,
                                    key=f"pay_{month}_{student_row['الكود']}"
                                )
                        
                        if st.form_submit_button("حفظ حالة الدفع"):
                            for month in self.months:
                                self.groups_df[self.current_group].loc[student_index, month] = updated_payment_status[month]
                            
                            # حفظ البيانات فوراً
                            self.save_data()
                            st.success("تم تحديث حالة الدفع بنجاح!")
                            time.sleep(1)
                            st.rerun()
                
                with tab3:
                    st.subheader("إدارة الاختبارات")
                    
                    # عرض الاختبارات الحالية
                    current_tests = student_row['الاختبارات']
                    if pd.notna(current_tests) and current_tests != '' and current_tests != 'nan':
                        st.markdown("#### نتائج الاختبارات الحالية")
                        tests = str(current_tests).split(';')
                        for test in tests:
                            test = test.strip()
                            if test and test != 'nan':
                                st.markdown(f"- {test}")
                    
                    # إضافة اختبار جديد
                    st.markdown("#### إضافة اختبار جديد")
                    test_name = st.text_input("اسم الاختبار", key="test_name")
                    test_score = st.text_input("الدرجة", key="test_score")
                    
                    if st.button("إضافة نتيجة الاختبار"):
                        if test_name and test_score:
                            new_test = f"{test_name}: {test_score}"
                            
                            if pd.isna(current_tests) or current_tests == '' or current_tests == 'nan':
                                updated_tests = new_test
                            else:
                                updated_tests = f"{current_tests}; {new_test}"
                            
                            self.groups_df[self.current_group].loc[student_index, 'الاختبارات'] = updated_tests
                            # حفظ البيانات فوراً
                            self.save_data()
                            st.success("تم إضافة نتيجة الاختبار بنجاح!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("الرجاء إدخال اسم الاختبار والدرجة")
                
                with tab4:
                    st.subheader("استرجاع QR Code للطالب")
                    
                    if st.button("🎫 إنشاء QR Code"):
                        qr_img = self.generate_qr_code(student_row['الكود'])
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.image(qr_img, caption=f"كود الطالب {student_row['الاسم']}", width=300)
                        with col2:
                            # تحويل الصورة إلى bytes للتحميل
                            img_bytes = BytesIO()
                            Image.open(qr_img).save(img_bytes, format="PNG")
                            img_bytes.seek(0)
                            
                            st.download_button(
                                label="📥 تحميل QR Code",
                                data=img_bytes,
                                file_name=f"qr_code_{student_row['الكود']}.png",
                                mime="image/png"
                            )
                
                with tab5:
                    st.subheader("حذف الطالب")
                    st.warning("⚠️ تنبيه: هذه العملية لا يمكن التراجع عنها!")
                    
                    if st.button("🗑️ حذف الطالب", key="delete_student_btn", type="primary"):
                        # حذف الطالب من المجموعة الحالية
                        self.groups_df[self.current_group] = self.groups_df[self.current_group].drop(student_index)
                        self.groups_df[self.current_group] = self.groups_df[self.current_group].reset_index(drop=True)
                        
                        # حفظ البيانات فوراً
                        self.save_data()
                        st.success("تم حذف الطالب بنجاح!")
                        time.sleep(2)
                        st.rerun()
            else:
                if search_query:
                    st.warning("لا يوجد طالب بهذا البحث")
        else:
            st.warning("لا يوجد طلاب مسجلين بعد")
    
    def view_analytics_tab(self):
        st.header("📊 الإحصائيات")
        
        # إنشاء تبويبات لكل مجموعة
        group_tabs = st.tabs([f"{group_name}" for group_name in self.groups_df.items()])
        
        for i, (group_name, df) in enumerate(self.groups_df.items()):
            with group_tabs[i]:
                st.subheader(f"إحصائيات مجموعة {group_name}")
                
                if not df.empty:
                    # قسم منفصل للبحث عن طالب معين
                    st.markdown("---")
                    st.subheader("🔍 البحث عن طالب معين")
                    
                    # تحديد المجموعة الحالية مؤقتاً للبحث
                    temp_current_group = self.current_group
                    self.current_group = group_name
                    
                    # خيارات البحث
                    search_option = st.radio(f"ابحث باستخدام في {group_name}:", ["الكود", "الاسم"], horizontal=True, key=f"search_{group_name}")
                    
                    student_data = pd.DataFrame()
                    
                    if search_option == "الكود":
                        search_query = st.text_input("اكتب كود الطالب", key=f"code_search_{group_name}")
                        if search_query:
                            suggestions = self.search_students(search_query, "code")
                            if suggestions:
                                selected_code = st.selectbox("الاقتراحات", suggestions, key=f"code_suggestions_{group_name}")
                                student_data = df[df['الكود'] == selected_code] if selected_code else pd.DataFrame()
                    else:
                        search_query = st.text_input("اكتب اسم الطالب", key=f"name_search_{group_name}")
                        if search_query:
                            suggestions = self.search_students(search_query, "name")
                            if suggestions:
                                selected_name = st.selectbox("الاقتراحات", suggestions, key=f"name_suggestions_{group_name}")
                                student_data = df[df['الاسم'] == selected_name] if selected_name else pd.DataFrame()
                    
                    # استعادة المجموعة الحالية
                    self.current_group = temp_current_group
                    
                    if not student_data.empty:
                        student_row = student_data.iloc[0]
                        
                        st.markdown("### بيانات الطالب المفصلة")
                        st.markdown('<div class="student-info">', unsafe_allow_html=True)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### المعلومات الشخصية")
                            st.markdown(f"""
                            - **الكود**: {student_row['الكود']}
                            - **الاسم**: {student_row['الاسم']}
                            - **رقم الهاتف**: {student_row['رقم_الهاتف']}
                            - **ولي الأمر**: {student_row['ولي_الامر']}
                            - **تاريخ التسجيل**: {student_row['تاريخ_التسجيل']}
                            - **الحصص الحاضرة**: {student_row['الحصص_الحاضرة']}
                            """)
                        
                        with col2:
                            st.markdown("#### حالة الدفع للأشهر")
                            months_paid = [month for month in self.months if student_row[month]]
                            months_not_paid = [month for month in self.months if not student_row[month]]
                            
                            st.markdown("**الأشهر المدفوعة:**")
                            for month in months_paid:
                                st.markdown(f"- {month.replace('_', ' ')} ✅")
                            
                            if months_not_paid:
                                st.markdown("**الأشهر غير المدفوعة:**")
                                for month in months_not_paid:
                                    st.markdown(f"- {month.replace('_', ' ')} ❌")
                        
                        # عرض تواريخ الحضور
                        attendance_dates = student_row['تواريخ_الحضور']
                        if pd.notna(attendance_dates) and attendance_dates != '' and attendance_dates != 'nan':
                            st.markdown("#### تواريخ الحضور")
                            dates = str(attendance_dates).split(';')
                            st.markdown('<div class="attendance-dates">', unsafe_allow_html=True)
                            for i, date_str in enumerate(dates, 1):
                                date_str = date_str.strip()
                                if date_str and date_str != 'nan':
                                    st.markdown(f"- الحصة {i}: {date_str}")
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        # عرض نتائج الاختبارات
                        test_results = student_row['الاختبارات']
                        if pd.notna(test_results) and test_results != '' and test_results != 'nan':
                            st.markdown("#### نتائج الاختبارات")
                            tests = str(test_results).split(';')
                            for test in tests:
                                test = test.strip()
                                if test and test != 'nan':
                                    st.markdown(f"- {test}")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # قسم منفصل لإحصائيات المجموعة ككل
                    st.markdown("---")
                    st.subheader("📈 إحصائيات المجموعة كاملة")
                    
                    total_students = len(df)
                    total_attendance = df['الحصص_الحاضرة'].sum()
                    avg_attendance = df['الحصص_الحاضرة'].mean() if total_students > 0 else 0
                    total_paid_months = df[self.months].sum().sum()
                    
                    cols = st.columns(4)
                    
                    with cols[0]:
                        st.markdown(f"""
                        <div class='stats-card'>
                            <div style='font-size: 24px;'>{total_students}</div>
                            <div>عدد الطلاب</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with cols[1]:
                        st.markdown(f"""
                        <div class='stats-card'>
                            <div style='font-size: 24px;'>{total_attendance}</div>
                            <div>إجمالي الحصص الحاضرة</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with cols[2]:
                        st.markdown(f"""
                        <div class='stats-card'>
                            <div style='font-size: 24px;'>{avg_attendance:.1f}</div>
                            <div>متوسط الحضور لكل طالب</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with cols[3]:
                        st.markdown(f"""
                        <div class='stats-card'>
                            <div style='font-size: 24px;'>{total_paid_months}</div>
                            <div>إجمالي الأشهر المدفوعة</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # مخطط حالات الدفع
                    if total_students > 0:
                        st.subheader("حالات الدفع للأشهر")
                        paid_counts = df[self.months].sum()
                        
                        fig = px.bar(
                            x=[m.replace('_', ' ') for m in self.months],
                            y=paid_counts.values,
                            labels={'x': 'الشهر', 'y': 'عدد الطلاب الذين دفعوا'},
                            color=paid_counts.values,
                            color_continuous_scale='blues'
                        )
                        fig.update_layout(
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font_color='white'
                        )
                        st.plotly_chart(fig, use_container_width=True, key=f"plotly_{group_name}_{i}")
                    
                    # عرض بيانات الطلاب
                    st.subheader("بيانات جميع الطلاب")
                    display_df = df.copy()
                    display_df['الكود'] = display_df['الكود'].astype(str)
                    
                    # تحويل قيم الأشهر المنطقية إلى نص
                    for month in self.months:
                        display_df[month] = display_df[month].map({True: '✅ مدفوع', False: '❌ غير مدفوع'})
                    
                    st.dataframe(display_df, use_container_width=True)
                    
                    # إنشاء ملف CSV للتصدير
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                    
                    st.download_button(
                        label=f"📥 تصدير بيانات {group_name} لملف CSV",
                        data=csv_data,
                        file_name=f"students_data_{group_name}_{date.today()}.csv",
                        mime="text/csv",
                        key=f"export_{group_name}"
                    )
                else:
                    st.warning("لا توجد بيانات متاحة للعرض في هذه المجموعة")

if __name__ == "__main__":
    system = StudentAttendanceSystem()


