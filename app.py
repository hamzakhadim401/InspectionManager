import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# --- 1. SETUP & CONNECTION ---
# Load the hidden keys from your .env file
load_dotenv()

# We use @st.cache_resource so Streamlit doesn't reconnect to the database on every single click
@st.cache_resource
def init_connection():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

# Initialize the Supabase client
supabase = init_connection()

# --- 2. PAGE CONFIGURATION ---
# This makes the app take up the full width of your monitor
st.set_page_config(page_title="Inspection Manager", layout="wide")





# --- AUTHENTICATION SECURITY GUARD ---
# Create a memory slot to remember if the user is logged in
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# If they are NOT logged in, show the login screen and STOP the app
if not st.session_state["authenticated"]:
    # We use columns to center the login box nicely
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("")
        st.write("")
        st.title("🔒 Admin Portal")
        st.info("Please enter the master password to access the system.")
        
        with st.form("login_form"):
            entered_password = st.text_input("Master Password", type="password")
            submit_login = st.form_submit_button("Log In", type="primary")
            
            if submit_login:
                # Check if what they typed matches the hidden .env password
                if entered_password == os.environ.get("ADMIN_PASSWORD"):
                    st.session_state["authenticated"] = True
                    st.rerun() # Refresh the page to clear the login screen
                else:
                    st.error("❌ Incorrect password.")
    
    # st.stop() acts as a brick wall. It stops Python from reading any code below this line!
    st.stop()



# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.title("Menu")
page = st.sidebar.radio("Navigate to:", ["Dashboard", "Inspectors","Clients & Vendors", "Inspection Inventory"])



if page == "Dashboard":
    st.title("📊 Company Dashboard")
    st.write("Welcome to your command center.")
    
    try:
        # 1. Fetch all data from the database
        insp_res = supabase.table("Inspections").select("*").execute()
        inspectors_res = supabase.table("Inspectors").select("*").execute()
        
        df_insp = pd.DataFrame(insp_res.data) if insp_res.data else pd.DataFrame()
        total_inspectors = len(inspectors_res.data) if inspectors_res.data else 0
        
        if not df_insp.empty:
            # --- SECTION 1: TOP METRICS ---
            total_inspections = len(df_insp)
            scheduled = len(df_insp[df_insp['status'] == 'Scheduled'])
            in_progress = len(df_insp[df_insp['status'] == 'In Progress'])
            completed = len(df_insp[df_insp['status'].isin(['Closed', 'Invoiced'])])
            
            # Display metrics in 4 neat columns
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Inspections", total_inspections)
            m2.metric("Active Inspectors", total_inspectors)
            m3.metric("Currently In Progress", in_progress)
            m4.metric("Completed / Invoiced", completed)
            
            st.divider()
            
            # --- SECTION 2: GRAPHS AND UPCOMING JOBS ---
            c1, c2 = st.columns([2, 1]) # Makes the chart column twice as wide as the list column
            
            with c1:
                st.subheader("📈 Inspections by Status")
                # Count how many jobs are in each status
                status_counts = df_insp['status'].value_counts().reset_index()
                status_counts.columns = ['Status', 'Count']
                
                # Create a beautiful Bar Chart
                fig = px.bar(status_counts, x='Status', y='Count', color='Status', text_auto=True)
                fig.update_layout(showlegend=False) # Hides the redundant legend
                st.plotly_chart(fig, use_container_width=True)
                
            with c2:
                st.subheader("📅 Upcoming (Next 7 Days)")
                # Find today's date and 7 days from now
                today = pd.to_datetime("today").normalize()
                next_week = today + pd.Timedelta(days=7)
                
                # Filter the dataframe for upcoming dates
                df_insp['start_date_dt'] = pd.to_datetime(df_insp['start_date'])
                upcoming = df_insp[(df_insp['start_date_dt'] >= today) & (df_insp['start_date_dt'] <= next_week)]
                
                if not upcoming.empty:
                    # Show a mini-table of just the crucial info
                    mini_table = upcoming[['Inspection_no', 'start_date', 'client_name']].sort_values(by='start_date')
                    st.dataframe(mini_table, hide_index=True, use_container_width=True)
                else:
                    st.info("No inspections scheduled for the next 7 days.")
                    
        else:
            st.info("No data available yet. Head over to the Inventory tab to schedule your first job!")
            
    except Exception as e:
        st.error(f"❌ Error loading dashboard data: {e}")







elif page == "Inspectors":
    st.title("👷 Manage Inspectors")
    
    # --- SECTION 1: ADD NEW INSPECTOR FORM ---
    st.subheader("Add New Inspector")
    
    # st.form creates a clean box for our inputs that only sends data when we click Submit
    with st.form("add_inspector_form", clear_on_submit=True):
        col1, col2 = st.columns(2) # Splits the form into two neat columns
        
        with col1:
            first_name = st.text_input("First Name")
            email = st.text_input("Email Address (For automated reminders)")
        with col2:
            last_name = st.text_input("Last Name")
            inspector_class = st.selectbox("Inspector Class", ["Mechanical", "Electrical", "Both"])
            location = st.text_input("Location") # NEW LOCATION FIELD
        submitted = st.form_submit_button("Save Inspector")
        
        # What happens when we click the button?
# What happens when we click the button?
        if submitted:
            if first_name and last_name and email: # Check if fields aren't empty
                try:
                    # NEW GATEKEEPER: Check if the email already exists in the database
                    existing_user = supabase.table("Inspectors").select("email").eq("email", email).execute()
                    
                    # If the database returns any data, it means the email is already there
                    if len(existing_user.data) > 0:
                        st.error(f"⚠️ Stop! An inspector with the email '{email}' already exists.")
                    else:
                        # If the email is new, proceed with saving
                        supabase.table("Inspectors").insert({
                            "name": first_name,
                            "surname": last_name,
                            "email": email,
                            "class": inspector_class,
                            "Location": location,
                        }).execute()
                        st.success(f"✅ Successfully added {first_name} {last_name}!")
                        st.rerun() # Automatically refreshes the page
                except Exception as e:
                    st.error(f"❌ Error saving to database: {e}")
            else:
                st.warning("⚠️ Please fill in the Name, Surname, and Email fields.")
    st.divider() # Draws a neat line across the screen

    # --- SECTION 2: VIEW ALL INSPECTORS ---
    st.subheader("Current Inspector Roster")
    try:
        # Ask Supabase for all rows in the inspectors table
        response = supabase.table("Inspectors").select("*").execute()
        inspectors_data = response.data
        
        if inspectors_data:
            # Display the data in a clean, interactive table
            st.dataframe(inspectors_data, use_container_width=True, hide_index=True)
        else:
            st.info("No inspectors added yet. Use the form above to add your first one!")
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
    # --- SECTION 3: DELETE INSPECTOR ---
    st.divider()
    st.subheader("🗑️ Delete Inspector")
    
    # We only show the delete tool if there are actually inspectors in the database
    if inspectors_data:
        # Create a dictionary to link what you see (Name + Email) to what the database needs (ID)
        inspector_options = {f"{ins['name']} {ins['surname']} ({ins['email']})": ins['id'] for ins in inspectors_data}
        
        with st.form("delete_inspector_form"):
            selected_inspector = st.selectbox("Select an Inspector to Remove", options=list(inspector_options.keys()))
            
            # The type="primary" makes the button stand out
            delete_submitted = st.form_submit_button("Delete Inspector", type="primary")
            
            if delete_submitted:
                inspector_id_to_delete = inspector_options[selected_inspector]
                try:
                    # Tell Supabase to delete the row where the ID matches
                    supabase.table("Inspectors").delete().eq("id", inspector_id_to_delete).execute()
                    st.success(f"✅ Successfully removed {selected_inspector} from the system!")
                    st.rerun() # Refresh to update the table and dropdown
                except Exception as e:
                    st.error(f"❌ Error deleting inspector: {e}")
    else:
        st.info("No inspectors available to delete.")









elif page == "Clients & Vendors":
    st.title("🏢 Manage Clients & Vendors")
    
    st.subheader("Add New Entity")
    with st.form("add_entity_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            entity_name = st.text_input("Company Name")
        with col2:
            entity_type = st.selectbox("Type", ["Client", "Vendor"])
            
        submit_entity = st.form_submit_button("Save Company")
        
        if submit_entity:
            if entity_name:
                try:
                    # Check for duplicates first
                    existing = supabase.table("clients_vendors").select("*").eq("name", entity_name).eq("type", entity_type).execute()
                    if len(existing.data) > 0:
                        st.error(f"⚠️ {entity_name} is already registered as a {entity_type}.")
                    else:
                        supabase.table("clients_vendors").insert({
                            "name": entity_name,
                            "type": entity_type
                        }).execute()
                        st.success(f"✅ Successfully added {entity_name}!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error saving to database: {e}")
            else:
                st.warning("⚠️ Please enter a company name.")
                
    st.divider()
    st.subheader("Current Database")
    try:
        entities_res = supabase.table("clients_vendors").select("*").execute()
        if entities_res.data:
            df_entities = pd.DataFrame(entities_res.data)
            
            # Show two side-by-side tables for clean viewing
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🤝 Clients**")
                clients = df_entities[df_entities['type'] == 'Client']
                st.dataframe(clients[['name']], hide_index=True, use_container_width=True)
            with c2:
                st.markdown("**🏭 Vendors**")
                vendors = df_entities[df_entities['type'] == 'Vendor']
                st.dataframe(vendors[['name']], hide_index=True, use_container_width=True)
        else:
            st.info("No clients or vendors added yet.")
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")









elif page == "Inspection Inventory":
    st.title("📋 Inspection Inventory")
    
    # --- MESSAGE HANDLER ---
    if 'temp_success' in st.session_state:
        st.success(st.session_state['temp_success'])
        del st.session_state['temp_success']
    if 'temp_warning' in st.session_state:
        st.warning(st.session_state['temp_warning'])
        del st.session_state['temp_warning']

    # Fetch data for dropdowns
    try:
        inspectors_res = supabase.table("Inspectors").select("*").execute()
        inspectors_list = inspectors_res.data
        inspector_dict = {f"{ins['name']} {ins['surname']} ({ins['class']})": ins['id'] for ins in inspectors_list} if inspectors_list else {}
        
        cv_res = supabase.table("clients_vendors").select("*").execute()
        cv_data = cv_res.data if cv_res.data else []
        client_names = [item['name'] for item in cv_data if item['type'] == 'Client']
        vendor_names = [item['name'] for item in cv_data if item['type'] == 'Vendor']
    except:
        inspector_dict, client_names, vendor_names = {}, [], []

    # --- SECTION 1: SMART SCHEDULING ---
    st.subheader("➕ Schedule New Inspection")
    with st.form("add_inspection_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            insp_no = st.text_input("Inspection No. (e.g., INSP-001)")
            po_no = st.text_input("PO Number")
            rfi_no = st.text_input("RFI Number")
        with col2:
            client = st.selectbox("Client Name", options=client_names if client_names else ["No clients found"])
            vendor = st.selectbox("Vendor Name", options=vendor_names if vendor_names else ["No vendors found"])
            location = st.text_input("Location (City/Country)")
        with col3:
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            selected_inspector = st.selectbox("Assign Inspector", options=list(inspector_dict.keys()) if inspector_dict else ["No inspectors available"])
        
        # --- NEW FINANCIALS SECTION ---
        st.markdown("**💰 Financial Details**")
        fin1, fin2 = st.columns(2)
        with fin1:
            revenue = st.number_input("Revenue (Inspector's Pay)", min_value=0, step=1)
        with fin2:
            profit = st.number_input("Profit (Company's Cut)", min_value=0, step=1)

        submit_insp = st.form_submit_button("Schedule Inspection", type="primary")

        if submit_insp:
            if not inspector_dict:
                st.error("⚠️ Please add an inspector first!")
            elif start_date > end_date:
                st.error("⚠️ The End Date cannot be before the Start Date!")
            elif not po_no or not rfi_no or not insp_no:
                st.warning("⚠️ Please fill in Inspection No, PO Number, and RFI Number.")
            else:
                po_check = supabase.table("Inspections").select("po_number").eq("po_number", po_no).execute()
                rfi_check = supabase.table("Inspections").select("rfi_number").eq("rfi_number", rfi_no).execute()
                
                if len(po_check.data) > 0:
                    st.error(f"🚨 FLAG: The PO Number '{po_no}' already exists! Save blocked.")
                elif len(rfi_check.data) > 0:
                    st.error(f"🚨 FLAG: The RFI Number '{rfi_no}' already exists! Save blocked.")
                else:
                    inspector_id = inspector_dict[selected_inspector]
                    existing_jobs = supabase.table("Inspections").select("*").eq("inspector_id", inspector_id).execute()
                    
                    conflict_msg = None
                    for job in existing_jobs.data:
                        job_start = pd.to_datetime(job['start_date']).date()
                        job_end = pd.to_datetime(job['end_date']).date()
                        if start_date <= job_end and end_date >= job_start:
                            conflict_msg = f"⚠️ DOUBLE BOOKING NOTE: {selected_inspector.split(' ')[0]} is also assigned to Inspection {job['inspection_no']} during these dates."
                            break
                    
                    # Calculate Total Automatically
                    total_amount = revenue + profit

                    try:
                        supabase.table("Inspections").insert({
                            "nspection_no": insp_no, "po_number": po_no, "rfi_number": rfi_no,
                            "inspector_id": inspector_id, "location": location,
                            "start_date": str(start_date), "end_date": str(end_date),
                            "client_name": client, "vendor_name": vendor, "status": "Scheduled",
                            "Revenue": revenue, "Profit": profit, "Total": total_amount # NEW FINANCIALS
                        }).execute()
                        st.session_state['temp_success'] = "✅ Inspection scheduled successfully!"
                        if conflict_msg: st.session_state['temp_warning'] = conflict_msg
                        st.rerun() 
                    except Exception as e:
                        st.error(f"❌ Error saving inspection: {e}")

    # --- SECTION 2: THE PRO INVENTORY DASHBOARD ---
    st.divider()
    
    try:
        inv_res = supabase.table("Inspections").select("*").execute()
        
        if inv_res.data:
            df = pd.DataFrame(inv_res.data)
            
            # --- NEW: GRAND TOTALS DISPLAY ---
            st.subheader("📊 Financial Summary")
            
            # Add them up (if the columns exist yet)
            tot_rev = df['Revenue'].sum() if 'Revenue' in df.columns else 0
            tot_prof = df['Profit'].sum() if 'Profit' in df.columns else 0
            tot_tot = df['Total'].sum() if 'Total' in df.columns else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Inspector Pay (Revenue)", f"{tot_rev:,.0f}")
            m2.metric("Total Company Cut (Profit)", f"{tot_prof:,.0f}")
            m3.metric("Grand Total Amount", f"{tot_tot:,.0f}")
            
            st.divider()
            st.subheader("📋 Central Inventory Log")

            # --- SEARCH & FILTERING ---
            f_col1, f_col2, f_col3 = st.columns([2, 2, 1])
            with f_col1:
                search_query = st.text_input("🔍 Search by PO, RFI, or Insp No.")
            with f_col2:
                status_filter = st.multiselect("Filter by Status", ["Scheduled", "In Progress", "Report Submitted", "Invoiced", "Closed"])
            
            if search_query:
                mask = df['po_number'].astype(str).str.contains(search_query, case=False) | \
                       df['rfi_number'].astype(str).str.contains(search_query, case=False) | \
                       df['inspection_no'].astype(str).str.contains(search_query, case=False)
                df = df[mask]
                
            if status_filter:
                df = df[df['status'].isin(status_filter)]

            # --- EXPORT TO EXCEL/CSV ---
            with f_col3:
                st.write("") 
                st.write("") 
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Download Data", data=csv_data, file_name='inspections_data.csv', mime='text/csv')

            # --- LIVE STATUS EDITING ---
            st.caption("💡 *Tip: Double-click a cell in the 'status' column to change it.*")
            
            edited_df = st.data_editor(
                df,
                column_config={
                    "status": st.column_config.SelectboxColumn(
                        "status", options=["Scheduled", "In Progress", "Report Submitted", "Invoiced", "Closed"], required=True
                    )
                },
                # Block everything except status from being edited
                disabled=["id", "inspection_no", "po_number", "rfi_number", "inspector_id", "location", "start_date", "end_date", "client_name", "vendor_name", "Revenue", "Profit", "Total"],
                use_container_width=True,
                hide_index=True,
                key="inventory_editor"
            )
            
            if st.button("💾 Save Status Changes", type="primary"):
                changes_made = False
                for index, row in edited_df.iterrows():
                    if df.loc[index, 'status'] != row['status']:
                        try:
                            supabase.table("Inspections").update({"status": row['status']}).eq("id", row['id']).execute()
                            changes_made = True
                        except Exception as e:
                            st.error(f"❌ Error updating {row['inspection_no']}: {e}")
                
                if changes_made:
                    st.session_state['temp_success'] = "✅ Database updated successfully!"
                    st.rerun()

            # --- DELETE INSPECTION ---
            st.divider()
            with st.expander("🗑️ Danger Zone: Delete an Inspection"):
                st.warning("Warning: Deleting an inspection is permanent and cannot be undone.")
                delete_options = {f"{row['inspection_no']} - {row['client_name']} (PO: {row['po_number']})": row['id'] for row in inv_res.data}
                
                with st.form("delete_inspection_form"):
                    selected_to_delete = st.selectbox("Select Inspection to Permanently Delete:", options=list(delete_options.keys()))
                    delete_btn = st.form_submit_button("🚨 Permanently Delete Record")
                    
                    if delete_btn:
                        delete_id = delete_options[selected_to_delete]
                        try:
                            supabase.table("Inspections").delete().eq("id", delete_id).execute()
                            st.session_state['temp_success'] = f"✅ Successfully deleted {selected_to_delete.split(' - ')[0]}!"
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error deleting inspection: {e}")

        else:
            st.info("No inspections scheduled yet. Add one above!")
    except Exception as e:
        st.error(f"❌ Error loading inventory: {e}")
