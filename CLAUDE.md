# CLAUDE.md - Project Context for Django Dental Support Organization

## Project Overview
Django-based dental support organization system with ongoing Tailwind CSS conversion.

## Recent Work (Last updated: 2025-08-07)

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
   