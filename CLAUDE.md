# CLAUDE.md - Project Context for Django Dental Support Organization

## Project Overview
Django-based dental support organization system with ongoing Tailwind CSS conversion.

## Recent Work (Last updated: 2025-09-04)

### Completed Tasks (2025-09-04)

1. **Fixed Cart Persistence After Login**
   - **Issue**: Cart items were not being preserved after user login due to Django session key cycling
   - **Solution Implemented**:
     - Created `PreserveCartSessionMiddleware` to store pre-login session key before authentication
     - Enhanced `merge_cart_on_login` signal to handle session key changes and find anonymous carts
     - Updated `get_cart()` function with fallback mechanism to recover missed carts
     - Added proper session configuration for cart persistence (2-week session cookies)
   - **Technical Details**:
     - Middleware stores old session key in `_old_session_key` before login
     - Signal checks multiple locations for anonymous cart (old key, current key, recent carts)
     - Cart items with options are properly merged preserving quantities and prices
     - Session engine set to database backend for reliability
   - **Files Modified**:
     - `shop/middleware.py`: Created new middleware for session preservation
     - `shop/signals.py`: Enhanced cart merging signal with better cart discovery
     - `shop/views.py`: Added fallback cart recovery in get_cart()
     - `core/settings.py`: Added middleware and session configuration
     - `accounts/adapter.py`: Already had session preservation code

### Completed Tasks (2025-08-15)

1. **Enhanced Accounting Integration and Payment Systems**
   - **Purchase Order Filtering**:
     - Fixed issue where draft purchase orders were being posted to general ledger
     - Only approved purchase orders (not draft status) are now posted to accounting
     - Added validation in both views and services to prevent draft posting
   - **Journal Entry Rollback/Delete Function**:
     - Added ability to delete/rollback posted journal entries
     - Automatically updates source documents (marks as unposted) when journal is deleted
     - Added confirmation page with full entry details before deletion
     - Dropdown menu in General Ledger with delete option for posted entries
     - Delete button in Journal Entry Detail page
   - **Automatic Payment Posting to Ledger**:
     - Sales payments (from invoice detail) now automatically post to accounting
     - Creates journal entries: DR Bank, CR Accounts Receivable
     - Shows journal entry number in success message
     - Handles both new payments and status changes to "completed"
   - **Supplier Payment System for Purchase Orders**:
     - Created SupplierPayment functionality for purchase orders
     - Added payment form with methods: Cash, Check, Wire Transfer, Credit Card, ACH
     - Automatic posting to ledger: DR Accounts Payable, CR Bank
     - Support for advance payments (prepayments)
     - Payment history tracking with status and approval system
   - **Payment History on Purchase Order Detail**:
     - Added comprehensive payment history section
     - Shows payment summary (total, paid, balance due)
     - Payment table with date, amount, method, status, and type
     - "Fully Paid" badge when balance is zero
     - Quick "Add Payment" button for recording new payments
   - **Template Fixes**:
     - Fixed purchase order delete template (changed base.html to base_daisyui.html)
     - Fixed dashboard URL reference (dashboard:home instead of dashboard:dashboard)
   - **Files Modified Today**:
     - `accounting/services.py`: Added rollback_journal_entry function, fixed draft PO posting
     - `accounting/views.py`: Added delete_journal_entry view, filtered draft POs from posting
     - `accounting/urls.py`: Added delete journal entry URL
     - `accounting/templates/`: Added confirm_delete_journal.html, updated general_ledger.html
     - `sales/views.py`: Added automatic payment posting in PaymentCreateView and PaymentUpdateView
     - `purchases/models.py`: SupplierPayment model (already existed)
     - `purchases/forms.py`: Added SupplierPaymentForm
     - `purchases/views.py`: Added supplier_payment_create view, updated purchase_order_detail
     - `purchases/urls.py`: Added supplier payment URL
     - `purchases/templates/`: Added supplier_payment_form.html, updated purchase_order_detail_daisyui.html

2. **Implemented Complete Accounting Module** (Earlier on 2025-08-15)
   - **Core Features**:
     - Double-entry bookkeeping system with journal entries and journal lines
     - Chart of accounts with account types (Asset, Liability, Revenue, Expense, Equity)
     - Automatic posting from sales invoices and purchase orders
     - Posted journal entries are automatically approved (not drafts)
   - **Admin Interface**:
     - Complete admin configuration with inline journal lines
     - Balance calculations and validation
     - Search and filter capabilities
   - **Financial Reports**:
     - Accounting Dashboard with key metrics (Cash, A/R, A/P, Revenue, Expenses)
     - General Ledger with filtering by account, date, and status
     - Trial Balance report
     - Income Statement (P&L)
     - Balance Sheet with retained earnings calculation
     - Chart of Accounts with balances
   - **Journal Entry Approval System**:
     - Individual entry approval/unapproval with balance validation
     - Status filtering (All, Posted, Draft)
     - Entries from sales/purchases are automatically posted (not drafts)
     - Manual entries can be created as drafts and require approval
   - **Integration**:
     - Sales invoices automatically create A/R and Revenue entries
     - Purchase orders automatically create Inventory/Expense and A/P entries
     - Payments create bank and A/R/A/P entries
     - Idempotent posting (prevents duplicate entries)
   - **Files Created/Modified**:
     - `accounting/admin.py`: Complete admin configuration
     - `accounting/views.py`: 8 views for dashboard and reports
     - `accounting/services.py`: Posting functions with posted=True
     - `accounting/templates/`: All templates with DaisyUI styling
     - `accounting/urls.py`: URL routing
     - Fixed account code 1200→1100 for Accounts Receivable

### Completed Tasks (2025-01-11)

1. **Fixed Payment Number Duplication Issue**
   - Changed payment number generation to include timestamp (YYYYMMDD-HHMMSS-MSS format)
   - Added microseconds for extra uniqueness to prevent concurrent duplicates
   - Example format: PAY-20250111-143025-123
   - Files modified:
     - `sales/forms.py`: Lines 611-616 - Updated PaymentForm.save() method

2. **Fixed Invoice Total Amount Rounding Issues**
   - Added proper rounding to 2 decimal places using Decimal.quantize()
   - Fixed precision issues like 115.631250000 displaying instead of 115.63
   - Applied rounding to all monetary fields (subtotal, tax_amount, shipping_cost, total_amount, etc.)
   - Files modified:
     - `sales/models.py`: Lines 412-457 - Updated calculate_totals() and recalculate_paid_amount()
     - `sales/views.py`: Multiple locations - Added rounding to payment calculations

3. **Added Tax Rate and Shipping Cost to Invoice Create Step 3**
   - Added tax rate input field with percentage display
   - Added shipping cost input field
   - Implemented session storage for tax and shipping values
   - Added "Update Preview" functionality to recalculate totals
   - Files modified:
     - `sales/templates/sales/invoice_create_step3_daisyui.html`: Lines 172-195
     - `sales/views.py`: Lines 550-558, 582-607 - Added context and POST handling

4. **Fixed Invoice List Statistics Display**
   - Implemented proper statistics calculation for current month
   - Fixed Revenue This Month font size (removed text-lg class)
   - Changed revenue display to integer format
   - Added date range filtering support
   - Added special handling for "overdue" status filter
   - Files modified:
     - `sales/views.py`: Lines 342-382 - Added get_context_data method to InvoiceListView
     - `sales/templates/sales/invoice_list_daisyui.html`: Line 40

5. **Improved Shipping Information Section Layout**
   - Moved "Create Shipment" button to header (matching Payment History section)
   - Button now always visible in upper right corner
   - Removed duplicate button from empty state
   - Files modified:
     - `sales/templates/sales/invoice_detail_daisyui.html`: Lines 444-449, 596-601

6. **Fixed Checkout Page Place Order Button**
   - Fixed missing shipping rate handling (defaults to free shipping)
   - Added JavaScript form validation with visual feedback
   - Added loading spinner on button click to prevent double submission
   - Improved error messages for better debugging
   - Files modified:
     - `shop/templates/shop/checkout.html`: Lines 288-293, 343-361
     - `shop/views.py`: Lines 540-554, 598-613

### Completed Tasks (2025-01-10)

1. **Enhanced Shop Navbar with Notification and Search Features**
   - **Added Notification System**:
     - Bell icon with dropdown menu for notifications
     - Badge indicator for unread notification count
     - Demo notifications with different types (order, product, offer)
     - Auto-refresh every minute for authenticated users
     - Links to customer portal notification center
   - **Implemented Product Search**:
     - Desktop: Search bar in navbar-center with DaisyUI join component
     - Mobile: Search button that opens modal dialog
     - Autocomplete suggestions with debouncing (300ms)
     - Quick search links for popular categories
     - Real-time search suggestions with highlighting
   - **Fixed Navbar Layout Issues**:
     - Restructured navbar using proper DaisyUI navbar-start/center/end classes
     - Fixed search bar being cut off by using navbar-center positioning
     - Set fixed width (w-80) for search input for consistency
     - Removed nested containers that were causing display issues
   - **Features Added**:
     - JavaScript functions for cart and notification updates
     - Search suggestion dropdown with product links
     - Responsive design with mobile modal for search
   - Files modified:
     - `shop/templates/shop/navbar.html`: Complete restructure with new features

2. **Staff Login Redirect to Admin Dashboard**
   - Modified authentication adapter to redirect staff/superusers to /home/
   - Prioritized staff check before customer check in login redirect logic
   - Regular customers still redirect to shop homepage
   - Files modified:
     - `accounts/adapter.py`: Lines 31-33 - Added staff user check first

### Completed Tasks (2025-08-10)

1. **Fixed Static and Media File Serving with DEBUG=False**
   - **Issue Identified**: 
     - CSS styles not loading when DEBUG=False
     - Product images returning 404 errors
     - Django doesn't serve static/media files in production mode by default
   - **Solutions Implemented**:
     - Installed and configured WhiteNoise middleware for static file serving
     - Added WhiteNoise to MIDDLEWARE after SecurityMiddleware
     - Configured STATICFILES_STORAGE for compressed static files
     - Created custom URL pattern using Django's serve view for media files
     - Media files now served via re_path when DEBUG=False
   - **Product Image Fix**:
     - Populated empty main_image and thumbnail_image fields from ProductImage gallery
     - Updated 27 out of 39 products with their primary gallery images
   - **Configuration Changes**:
     - `core/settings.py`: Added WhiteNoise middleware and storage backend
     - `core/urls.py`: Added conditional media file serving for DEBUG=False
     - `templates/base.html`: Removed duplicate vite_asset tags
   - **Important Notes**:
     - Solution suitable for local development and testing
     - Production environments should use Nginx/Apache for media files
     - WhiteNoise handles static files, custom view handles media files

2. **Redesigned Product List Page with DaisyUI**
   - **Converted from Tailwind Elements to DaisyUI**: Complete redesign using DaisyUI components
   - **Component Updates**:
     - Cards for product display with hover effects
     - Drawer component for mobile filters
     - Dropdown for sort options
     - Breadcrumbs for navigation hierarchy
     - Badges for category counts
     - Join (button group) for pagination
     - Hero component for empty state
     - Toast notifications for cart actions
   - **Layout Improvements**:
     - Removed duplicate sidebar (was showing two sidebars)
     - Responsive grid (1 column on mobile, up to 4 on XL screens)
     - Mobile-friendly drawer for filters on smaller screens
   - **User Experience Enhancements**:
     - Removed stock status badges per request
     - Added intcomma filter for price formatting (e.g., $1,234.56)
     - Made product images clickable to navigate to detail page
     - Smooth transitions on hover
     - Clear visual feedback for actions
   - Files modified:
     - `shop/templates/shop/product_list.html`: Complete template rewrite using DaisyUI

3. **Added Document Downloads to Product Detail Page**
   - **Backend Changes**:
     - Updated shop view to pass public documents to template
     - Added filtering for `is_public=True` documents only
   - **Frontend Implementation**:
     - Created "Downloads & Documents" section after specifications
     - Responsive grid layout (1 column mobile, 2 on desktop)
     - Document cards showing:
       - Document icon (red for PDFs, gray for others)
       - Title and description
       - Document type badge
       - File size (using filesizeformat filter)
       - Download button with icon
   - **Features**:
     - Direct download links for product documentation
     - Clean card-based layout using DaisyUI
     - Only shows section if documents are available
   - Files modified:
     - `shop/views.py`: Line 145 - Added documents to context
     - `shop/templates/shop/product_detail.html`: Lines 245-297 - Added documents section

4. **Updated My Orders Page to Show Shipping Status**
   - **Replaced Order Status with Shipping Information**:
     - Changed from general order status to specific shipping status
     - Shows first shipment status for each order
     - Color-coded badges for different shipping states:
       - Delivered: Green (success)
       - Shipped/In Transit: Blue (primary)
       - Out for Delivery: Accent
       - Failed/Returned: Red (error)
       - Awaiting Shipment: Gray (ghost)
   - **Added Tracking Details**:
     - Displays carrier name and tracking number
     - Shows in compact format next to status badge
   - **Enhanced Expanded Order View**:
     - Added "Shipment Details" section
     - Shows all shipments for multi-supplier orders
     - Displays shipped date, estimated delivery, actual delivery
     - Grid layout for shipping address and shipment details
   - **Performance Optimization**:
     - Added `prefetch_related('shipments', 'items')` to prevent N+1 queries
   - Files modified:
     - `customer_portal/templates/customer_portal/order_list.html`: Lines 116-148, 266-320
     - `customer_portal/views.py`: Line 119 - Added prefetch_related

### Completed Tasks (2025-08-09)

1. **Fixed Shop Navigation Layout Issues**
   - **Fixed Navbar Structure**: Corrected broken navbar in shop base template where menu items weren't aligning properly
   - **Improved Navbar Layout**: Removed problematic max-width container wrapper and added proper padding directly to navbar
   - **Fixed Menu Alignment**: Ensured navbar-start, navbar-center, and navbar-end are direct children of navbar div for proper flex behavior
   - **Enhanced DaisyUI Integration**: Fixed navbar to use proper DaisyUI navbar component structure
   - Files modified:
     - `shop/templates/shop/base.html`: Lines 11-133 - Complete navbar restructure

2. **Updated Shop to Tailwind Elements**
   - **Migrated from DaisyUI to Tailwind Elements**: Shop template now uses Tailwind Elements for advanced UI components
   - **Added Advanced Navigation**: Implemented mega menus with popover functionality for desktop navigation
   - **Mobile Menu Enhancement**: Added slide-out mobile menu with tab groups and comprehensive navigation
   - **Enhanced User Experience**: Improved search functionality and cart dropdown with better styling
   - **Added Tailwind Elements CDN**: Included `@tailwindplus/elements` for advanced interactive components
   - Files modified:
     - `shop/templates/shop/base.html`: Complete template rewrite using Tailwind Elements
   - Note: This represents a major UI framework change from DaisyUI to Tailwind Elements for the shop module

3. **Enhanced Product Detail Page UI**
   - **Improved Image Layout**: Made images smaller in "Customers also purchased" section (height reduced from 192px to 128px)
   - **Increased Grid Density**: Changed grid from 3 columns to 4 columns on large screens for better product display
   - **Better Spacing**: Increased gap between labels and form inputs for better visual hierarchy
   - **Fixed Category Links**: Corrected sidebar category links to use absolute URLs instead of relative ones
   - Files modified:
     - `shop/templates/shop/product_detail.html`: Lines 250-284 - Product grid and image improvements

4. **Fixed Checkout Page Issues**
   - **Added Missing Place Order Button**: Updated checkout template to use proper DaisyUI button styling
   - **Enhanced Button Styling**: Changed from plain Tailwind to DaisyUI `btn btn-primary btn-block btn-lg` classes
   - **Added Visual Feedback**: Included checkmark icon for better user experience
   - **Improved Button Text**: Changed from "Complete order" to "Place Order" for clarity
   - Files modified:
     - `shop/templates/shop/checkout.html`: Lines 327-332 - Button enhancement

5. **Fixed Customer Portal Order Detail Design**
   - **Complete Template Conversion**: Converted from plain Tailwind CSS to DaisyUI components
   - **Enhanced Order Timeline**: Replaced complex timeline markup with DaisyUI's steps component
   - **Improved Data Display**: Used card layouts, badges, and tables for better information presentation
   - **Better Navigation**: Updated breadcrumb to use DaisyUI breadcrumbs component
   - **Enhanced Actions**: Updated buttons to use proper DaisyUI button styling
   - Files modified:
     - `customer_portal/templates/customer_portal/order_detail.html`: Complete template rewrite using DaisyUI

### Completed Tasks (2025-08-08)

1. **Implemented Complete Shipment Management System**
   - **Enhanced Invoice Detail Page** with shipment management:
     - Added edit/delete dropdown menu for each shipment
     - Displays full shipping address information
     - View Details, Edit Shipment, and Delete Shipment options
     - Confirmation modal for safe shipment deletion
     - JavaScript-powered dynamic delete confirmation
   
   - **Advanced Shipping Address Management**:
     - Smart address selection (multiple vs single address handling)
     - Manual address editing with full form fields
     - Auto-population from customer addresses
     - Clear/edit address functionality with dropdown options
     - Background sync between address selection and manual fields
   
   - **Shipment Form Improvements**:
     - Fixed form validation errors for ship_to_* fields
     - Made shipping address fields optional with auto-population
     - Added prominent user guidance for item selection
     - Client-side validation prevents empty shipments
     - Enhanced UX with clear instructions and error prevention
   
   - **Technical Fixes**:
     - Added `django.contrib.humanize` to INSTALLED_APPS
     - Fixed TemplateSyntaxError for humanize template tags
     - Resolved shipment items not displaying (empty formset issue)
     - Added form validation to ensure items are selected
   
   - **Files Modified**:
     - `sales/templates/sales/invoice_detail_daisyui.html`: Lines 419-556 - Enhanced shipment display with dropdown menus
     - `sales/templates/sales/shipment_form.html`: Lines 264-536 - Complete address management system
     - `sales/forms.py`: Lines 541-548 - Made shipping fields optional
     - `core/settings.py`: Line 49 - Added humanize to INSTALLED_APPS

2. **Implemented Rich Text Editor for Product Long Description**
   - Added Summernote widget to ProductForm for long_description field
   - Updated product/forms.py to import and use SummernoteWidget
   - Modified product form template to include Summernote media assets
   - Added custom CSS styling to match DaisyUI theme
   - Rich text editor now available for product descriptions matching Blog content functionality
   - Files modified:
     - `product/forms.py`: Line 79 - Changed from Textarea to SummernoteWidget
     - `product/templates/product/product_form.html`: Lines 5-25 - Added form.media and custom styles
   - Tested and verified working with proper initialization

### Completed Tasks (2025-08-07)

1. **Implemented Factory Portal System**
   - Created FactoryUser model linked to Supplier with roles and permissions
   - Built complete factory portal interface similar to customer portal
   - Features:
     - Factory dashboard with work order statistics
     - Work order management with status updates
     - Fulfillment item tracking and updates
     - Shipment creation and management
     - Supply request monitoring
     - Profile management for factory users
   - Access control based on factory user roles (manager, supervisor, worker, quality, shipping)
   - Supplier-specific work order filtering
   - URL: `/factory/` for factory user portal

2. **Added Supplier Field to Product Model**
   - Added ForeignKey relationship from Product to Supplier
   - Used string reference "purchases.Supplier" to avoid circular imports
   - Updated ProductForm to include supplier field in forms
   - Added supplier field to product create/update templates
   - Added supplier display in product detail view with link to supplier detail
   - Added supplier column to product list view
   - Migration applied successfully: `0009_product_supplier.py`

3. **Enhanced Factory Portal**
   - Created profile and change password templates matching customer portal theme
   - Fixed template block naming issue (changed from factory_content to content)
   - Added customer orders section to factory dashboard
   - Factory users now see all customer invoice items for products from their supplier
   - Customer orders display includes invoice number, customer, product, quantity, price, and status
   - **Added Packing Slip Feature**:
     - Created separate packing slip view for factory users (no price information)
     - Invoice links in dashboard now open packing slip instead of regular invoice
     - Packing slip shows order info, shipping address, items, quantities, and special instructions
     - Highlights supplier's own products in blue
     - Includes print functionality with clean print styles
     - Access control ensures factory users can only view packing slips with their products

4. **Added Supplier Info to Invoice Details**
   - Added supplier information display in invoice item rows
   - Shows supplier name with link to supplier detail page
   - Only displays when product has a supplier assigned

5. **Fixed Product Category Display**
   - Updated product detail template to use `product.category.name` instead of deprecated `get_category_display`
   - Added proper null checking for category field

### Completed Tasks (2025-01-09)

1. **Implemented Hierarchical Category System for Products**
   - Created new Category model with parent-child relationships (unlimited depth)
   - Migrated from CharField with choices to ForeignKey relationship
   - Added helper methods for hierarchy navigation (get_ancestors, get_descendants, get_level, etc.)
   - Created Category admin interface with product count display
   - Preserved existing product categories during migration

2. **Enhanced Purchase Order Detail Page**
   - Added inventory tracking for serial number managed items
   - Shows "X / Y created" format with visual indicators for pending items
   - Added "View All Inventory" feature that displays inline (removed modal approach)
   - Displays inventory items grouped by product with serial numbers, status, and warranty info
   - Added links to view individual inventory items

3. **Updated Purchase Order Create Step 1**
   - Changed from dropdown select to supplier list with radio buttons
   - Added search functionality to filter suppliers
   - Displays supplier details inline (contact, email, location, active status)
   - Matches the UI pattern of invoice creation for consistency

4. **Fixed Decimal Conversion Errors**
   - Added proper validation for tax_rate, shipping_cost, and discount_percent
   - Fixed InvalidOperation errors in both create and edit views
   - Handles empty strings, None, and invalid values gracefully

5. **Enhanced Serial Number Validation**
   - Added duplicate checking within submitted serial numbers
   - Improved error messages showing exactly which serial numbers are duplicates
   - Prevents both internal duplicates and conflicts with existing inventory

### Completed Tasks (2025-08-04)

1. **Applied Invoice App Design to Purchase Orders**
   - Converted all purchase order templates to Tailwind CSS
   - Implemented consistent UI patterns across the module

2. **Implemented Inventory Registration for Serial Number Managed Items**
   - Added "Register inventory" button in purchase order detail for serial-numbered items
   - Created modal for entering multiple serial numbers (comma-separated)
   - Fixed validation errors preventing inventory creation before items received
   - Fixed warranty calculation issues (commented out due to missing python-dateutil)

3. **Fixed Various UI/UX Issues**
   - Fixed inventory detail page missing sidebar/navigation (block name issue)
   - Fixed autoArrange() function in diagrams.html to prevent box overlaps
   - Added ability to select serial number managed inventory when creating sales invoices
   - Added related purchase order info with links on inventory detail page
   - Fixed inventory delete page 404 errors
   - Added delete buttons for invoice items in update form
   - Fixed invoice delete button URL generation
   - Changed breadcrumb "Dashboard" text to home icon
   - Removed Orders menu from sidebar

4. **Migrated Purchases App to New Supplier Model Structure**
   - Created normalized Supplier, SupplierContact, SupplierDocument models
   - Updated all purchase order views, forms, and templates
   - Implemented full CRUD operations for suppliers
   - Added dynamic contact management without page reload
   - Fixed template syntax errors and aggregate calculations

5. **Implemented 3-Step Process for Purchase Orders (Create & Edit)**
   - **Step 1**: Select supplier and dates
   - **Step 2**: Add/edit products with real-time calculations
   - **Step 3**: Review and save
   - Features:
     - Session-based data persistence between steps
     - Progress indicators
     - Dynamic supplier information display
     - Inline additional details (tax, shipping, discount, notes)
   - Fixed date validation errors and Decimal/float type mismatches

### Previous Completed Tasks
- Removed checkboxes from list views (Customer, Blog, Campaign, Target Groups)
- Added Sender Information Feature with SMTP configuration
- Fixed Target Group Cart Page styling

### Pending Tasks (from TODO list)
1. Convert Blog templates to Tailwind CSS
2. Convert remaining Campaign templates to Tailwind CSS
3. Convert Target Group templates to Tailwind CSS
4. Convert Dashboard base template to Tailwind CSS

### Technical Stack
- Django 5.2.4
- Tailwind CSS v4
- PostgreSQL database
- Django Allauth for authentication
- Vite for asset bundling
- Use function based view rather than Class view except the Built-in Class

### Important Commands
```bash
# Run development server
python manage.py runserver

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Tailwind CSS (if needed)
npm run dev
```

### Technical Notes

#### Accounting Module Implementation
- **Double-Entry Bookkeeping**: Every transaction creates balanced journal entries
- **Chart of Accounts**: 
  - 1010: Bank - Checking
  - 1100: Accounts Receivable (not 1200 which is Inventory)
  - 2000: Accounts Payable
  - 4000: Sales Revenue
  - 2200: Sales Tax Payable
- **Automatic Posting**:
  - Sales invoices → DR: A/R (1100), CR: Revenue (4000) + Tax (2200)
  - Purchase orders → DR: Inventory/Expense, CR: A/P (2000)
  - Payments → DR: Bank (1010), CR: A/R (1100)
  - All automated entries are created with `posted=True` (not drafts)
- **Journal Entry Approval**:
  - Individual approval/unapproval with balance validation
  - Entries must be balanced (total debits = total credits) to be approved
  - Filter by status: All, Posted, Draft
- **Idempotent Posting**: 
  - Multiple calls with same document create only one journal entry
  - Existing entries are returned without duplication
- **Access URLs**:
  - Dashboard: `/home/accounting/`
  - General Ledger: `/home/accounting/general-ledger/`
  - Trial Balance: `/home/accounting/trial-balance/`
  - Income Statement: `/home/accounting/income-statement/`
  - Balance Sheet: `/home/accounting/balance-sheet/`
  - Post Documents: `/home/accounting/post-documents/`

#### Purchase Order 3-Step Process Implementation
- Views: `PurchaseOrderCreateStep1View`, `PurchaseOrderCreateStep2View`, `PurchaseOrderCreateStep3View`
- Edit Views: `PurchaseOrderEditStep1View`, `PurchaseOrderEditStep2View`, `PurchaseOrderEditStep3View`
- Uses Django sessions to maintain state between steps
- URLs: `/purchases/orders/create/step1/`, `/step2/`, `/step3/` (same pattern for edit)
- Purchase Order Create's 1st step should have the supplier list, not select box, like the invoice create's 1st page.


#### Type Safety Fix for Purchase Orders
- Issue: `TypeError: unsupported operand type(s) for *: 'float' and 'decimal.Decimal'`
- Solution: Store numeric values as strings in session, convert to Decimal when creating/updating items
- Updated `PurchaseOrderItem.save()` to handle type conversion explicitly

#### Inventory Creation
- Accessible from purchase order detail when item is serial number managed
- Modal-based UI for entering multiple serial numbers
- Creates individual inventory records for each serial number
- Links inventory to purchase order via `purchase_order_number` field

### Known Issues/Notes
- python-dateutil not installed (warranty calculations commented out)
- All numeric fields in purchase orders use Decimal type for precision
- Supplier model is now normalized with separate contact management
- Category model supports unlimited hierarchy depth
- Inventory list view supports filtering by purchase_order parameter

### Next Steps
- Install python-dateutil and uncomment warranty calculation code
- Continue Tailwind CSS conversion for Blog and Campaign modules
- Consider adding bulk operations for inventory management
- Add category breadcrumb navigation in product views
- Implement category-based product filtering

### Creating inventory
- Process
   1. Create a purchase order
   2. Add a product as a item of the purchase.
   3. Save a purchase order.
   4. if the product is managed by the serial number - check 'is_serial_number_cheched' field, there is a inventory creating button.
   5. if the user click the inventory creation button. the inventory creation modal window opens.
   6. the inventory creation modal window has a serial number input box which multiple serial numbers allowed by comma. 
   7. When saving the inventory, the inventory will be created in the Inventory model.
   

### Customer Creation on User Registration
   1. When a user signs up, a Customer record is automatically created
   2. Implementation approach:
      - Use Django signals (post_save) on User model
      - Create Customer with basic info from User (email, first_name, last_name)
      - Link Customer to User with OneToOneField
   3. In the Profile page, there should be the customer information update form
      - Allow users to update their customer details (phone, company, address, etc.)
      - customer_portal.views.profile_view already handles this
   4. Access pattern:
      - Use `request.user.customer` to access customer from user
      - Handle cases where customer might not exist (create on demand) 

### Factory Management System (Added: 2025-01-09)

#### Overview
Comprehensive supply chain management system for handling order fulfillment and shipping.

#### Key Components:

1. **WorkOrder Model**
   - Tracks fulfillment of invoice items
   - Priority levels: Low, Normal, High, Urgent
   - Status: Pending → In Progress → Ready → Shipped → Completed
   - Progress tracking with percentage calculation
   - Department/user assignment

2. **FulfillmentItem Model**
   - Individual item tracking within work orders
   - Inventory allocation management
   - Quantity tracking (ordered/allocated/fulfilled)
   - Warehouse location tracking
   - Quality check support

3. **Shipment Model**
   - Multi-carrier support (UPS, FedEx, USPS, DHL, etc.)
   - Tracking number management
   - Auto-populates shipping address from invoice
   - Package details (weight, dimensions)
   - Cost tracking (shipping + insurance)
   - Document generation flags

4. **SupplyRequest Model**
   - Supply request workflow
   - Approval system
   - Urgency levels
   - Links to purchase orders

#### Workflow:
1. Invoice created → Work Order generated
2. Inventory allocated to items
3. Items fulfilled after quality check
4. Shipment created with tracking
5. Delivery confirmation

#### Admin Features:
- Visual progress bars for work orders
- Inline editing of fulfillment items
- Quick actions for status updates
- Automatic number generation (WO-XXXXXX, SHIP-XXXXXX, SR-XXXXXX)

#### Usage:
- Admin Access: `/admin/factory/`
- Factory Portal: `/factory/` (for factory users)
- Create work orders from invoices
- Allocate inventory to fulfill orders
- Create and track shipments
- Manage supply requests

### Factory Portal System

#### Overview:
Factory users (linked to suppliers) have their own portal to manage work orders and shipments.

#### FactoryUser Model:
- Linked to Django User and Supplier
- Roles: manager, supervisor, worker, quality, shipping
- Permissions for different operations
- Employee ID and department tracking

#### Factory Portal Features (`/factory/`):
- **Dashboard**: Statistics, recent orders, pending supplies
- **Work Orders**: View and manage supplier-specific orders
- **Shipments**: Create and track shipments
- **Supply Requests**: Monitor and approve supply needs
- **Profile**: Manage factory user profile

#### Access Control:
- Factory users only see work orders for their supplier's products
- Role-based permissions for updating orders and creating shipments
- Managers/supervisors can approve orders and supply requests

#### Creating Factory Users:
1. Create a regular Django user account
2. Create FactoryUser record in admin linking to user and supplier
3. Set appropriate role and permissions
4. User can then login and access `/factory/` portal
   