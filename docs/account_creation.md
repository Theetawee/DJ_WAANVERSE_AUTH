### **Account Creation Flow**  

#### **Step 1: User Provides Basic Information**  
- The user submits at least **one** of `email_address`, `phone_number`, or `username`.  
- If `email_address` or `phone_number` is provided, an OTP is sent for verification.  
- The account is created in a **"pending verification"** state.  

#### **Step 2: Verification (If Required)**  
- The user enters the OTP sent to their email or phone.  
- Once verified, update `email_verified=True` or `phone_number_verified=True`.  
- If neither email nor phone was provided, skip this step.  

#### **Step 3: Complete Profile (Optional)**  
- The user can add additional details like full name, country, or preferences.  
- If KYC is required, prompt for document uploads.  

#### **Step 4: Accept Terms & Conditions**  
- The user must accept the platform’s policies before proceeding.  

#### **Step 5: Activate Account**  
- If verification (Step 2) was successful and required details are provided, set `is_active=True`.  
- If KYC is needed, keep the account in **"kyc_pending"** status until approval.  

#### **Step 6: Onboarding & Access**  
- The user is redirected to their dashboard.  
- If KYC is required, restrict financial actions until approval.  

This ensures **flexibility, security, and a smooth user experience**. Do you want to tweak any part of the flow?