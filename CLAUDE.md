# CLAUDE.md - Project Context for Django Dental Support Organization

## Project Overview
Django-based dental support organization system with ongoing Tailwind CSS conversion.

## Recent Work (Last updated: 2025-08-10)

### Completed Tasks (2025-08-10)

1. **Redesigned Product List Page with DaisyUI**
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

2. **Added Document Downloads to Product Detail Page**
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

3. **Updated My Orders Page to Show Shipping Status**
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
   