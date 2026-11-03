-- S1-DBA-05 (1/2): seed data for roles, modules and the per-action rights catalogue (36 rights, guide 3.8).
-- Needs S1-DBA-03 applied first. Safe to re-run: existing rows are left alone.
-- Stamps ('ADD <user> <time>') are filled in by the database triggers.

-- Default roles (guide 1.2)
INSERT INTO role (role_code, role_name, description) VALUES
    ('superadmin', 'Superadmin', 'System owner: everything, including System Settings'),
    ('admin', 'Admin', 'Manager: most modules and user rights; cannot see Superadmin accounts'),
    ('user', 'User', 'Staff: only the modules and actions an Admin has granted')
ON CONFLICT (role_code) DO NOTHING;

-- Modules (the sidebar and the Rights dialog)
INSERT INTO module (module_code, module_name, sort_order) VALUES
    ('customer', 'Customer Management', 1),
    ('product', 'Product Management', 2),
    ('hr', 'Human Resources', 3),
    ('sales', 'Sales', 4),
    ('reports', 'Reports', 5)
ON CONFLICT (module_code) DO NOTHING;

-- Rights catalogue: one row per checkbox in the Rights dialog (3 + 6 + 13 + 7 + 7 = 36).
-- perm_code uses the same keys as the prototype (public/js/app.js), so the front end and database agree.
INSERT INTO permission (perm_code, module_code, perm_name, sort_order) VALUES
    ('customers.add', 'customer', 'Add Customer', 1),
    ('customers.edit', 'customer', 'Edit Customer', 2),
    ('customers.delete', 'customer', 'Delete Customer', 3),
    ('products.add', 'product', 'Add Product', 1),
    ('products.edit', 'product', 'Edit Product', 2),
    ('products.delete', 'product', 'Delete Product', 3),
    ('products.priceAdd', 'product', 'Add Price', 4),
    ('products.priceEdit', 'product', 'Edit Price', 5),
    ('products.priceDelete', 'product', 'Delete Price', 6),
    ('hr.jobAdd', 'hr', 'Add Job', 1),
    ('hr.jobEdit', 'hr', 'Edit Job', 2),
    ('hr.jobDelete', 'hr', 'Delete Job', 3),
    ('hr.deptAdd', 'hr', 'Add Department', 4),
    ('hr.deptEdit', 'hr', 'Edit Department', 5),
    ('hr.deptDelete', 'hr', 'Delete Department', 6),
    ('hr.empAdd', 'hr', 'Add Employee', 7),
    ('hr.empEdit', 'hr', 'Edit Employee', 8),
    ('hr.empDelete', 'hr', 'Delete Employee', 9),
    ('hr.jhView', 'hr', 'View Job History', 10),
    ('hr.jhAdd', 'hr', 'Add Job History', 11),
    ('hr.jhEdit', 'hr', 'Edit Job History', 12),
    ('hr.jhDelete', 'hr', 'Delete Job History', 13),
    ('sales.add', 'sales', 'Add Sale', 1),
    ('sales.edit', 'sales', 'Edit Sale', 2),
    ('sales.delete', 'sales', 'Delete Sale', 3),
    ('sales.detailView', 'sales', 'View Sale Details', 4),
    ('sales.detailAdd', 'sales', 'Add Sale Detail', 5),
    ('sales.detailEdit', 'sales', 'Edit Sale Detail', 6),
    ('sales.detailDelete', 'sales', 'Delete Sale Detail', 7),
    ('reports.topCustomers', 'reports', 'Top Customers', 1),
    ('reports.productMaster', 'reports', 'Product Master List', 2),
    ('reports.topProducts', 'reports', 'Top Products', 3),
    ('reports.activeEmployees', 'reports', 'Active Employees', 4),
    ('reports.allEmployees', 'reports', 'All Employees', 5),
    ('reports.empJobHistory', 'reports', 'Employee Job History', 6),
    ('reports.topSales', 'reports', 'Top Sales', 7)
ON CONFLICT (perm_code) DO NOTHING;
