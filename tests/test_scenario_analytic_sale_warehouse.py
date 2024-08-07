import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import create_chart, get_accounts
from trytond.modules.account_invoice.tests.tools import create_payment_term
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Activate analytic_sale_warehouse
        config = activate_modules('analytic_sale_warehouse')

        # Create company
        _ = create_company()
        company = get_company()

        # Reload the context
        User = Model.get('res.user')
        Group = Model.get('res.group')
        config._context = User.get_preferences(True, config.context)

        # Create sale user
        sale_user = User()
        sale_user.name = 'Sale'
        sale_user.login = 'sale'
        sale_group, = Group.find([('name', '=', 'Sales')])
        sale_user.groups.append(sale_group)
        sale_user.save()

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create an analytic hierarchy
        AnalyticAccount = Model.get('analytic_account.account')
        root1 = AnalyticAccount(name='Root 1', type='root')
        root1.save()
        analytic_account = AnalyticAccount(name='Account 1.1', root=root1)
        root1.childs.append(analytic_account)
        analytic_account = AnalyticAccount(name='Account 1.2', root=root1)
        root1.childs.append(analytic_account)
        root1.save()

        # Create a second analytic hierarchy
        root2 = AnalyticAccount(name='Root 1', type='root')
        root2.save()
        analytic_account = AnalyticAccount(name='Account 2.1', root=root2)
        root2.childs.append(analytic_account)
        analytic_account = AnalyticAccount(name='Account 2.2', root=root2)
        root2.childs.append(analytic_account)
        root2.save()

        # Create parties
        Party = Model.get('party.party')
        customer = Party(name='Customer')
        customer.save()

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        template = ProductTemplate()
        template.name = 'product'
        template.account_category = account_category
        template.default_uom = unit
        template.type = 'goods'
        template.salable = True
        template.list_price = Decimal('10')
        template.cost_price_method = 'fixed'
        template.save()
        product, = template.products
        product.save()

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Create a warehouse with assigned analytic accounts
        Location = Model.get('stock.location')
        input_loc2 = Location(name='Input 2')
        input_loc2.save()
        output_loc2 = Location(name='Output 2')
        output_loc2.save()
        storage_loc2 = Location(name='Storage 2')
        storage_loc2.save()
        warehouse2, = Location.create([{
            'name': 'Warehouse 2',
            'type': 'warehouse',
            'input_location': input_loc2.id,
            'output_location': output_loc2.id,
            'storage_location': storage_loc2.id,
        }], config.context)
        warehouse2 = Location(warehouse2)
        company_location = warehouse2.companies.new()
        self.assertEqual(len(company_location.analytic_accounts), 2)

        for entry in company_location.analytic_accounts:
            if entry.root.id == root1.id:
                entry.account = root1.childs[0]
            else:
                entry.account = root2.childs[-1]

        warehouse2.save()
        self.assertEqual(
            warehouse2.companies[0].analytic_accounts[0].account.name,
            'Account 1.1')
        self.assertEqual(
            warehouse2.companies[0].analytic_accounts[1].account.name,
            'Account 2.2')

        # Prepare sale to warehouse without analytic accounts
        config.user = sale_user.id
        Sale = Model.get('sale.sale')
        warehouse1, = Location.find([('code', '=', 'WH')])
        sale = Sale()
        sale.party = customer
        sale.warehouse = warehouse1
        sale.payment_term = payment_term
        sale.invoice_method = 'order'
        sale_line = sale.lines.new()
        sale_line.product = product
        sale_line.quantity = 2.0
        sale.save()
        self.assertEqual(len(sale.lines[0].analytic_accounts), 2)
        self.assertEqual(
            all(e.account == None for e in sale.lines[0].analytic_accounts),
            True)

        # Prepare sale to warehouse with analytic accounts
        sale = Sale()
        sale.party = customer
        sale.warehouse = warehouse2
        sale.payment_term = payment_term
        sale.invoice_method = 'order'
        sale_line = sale.lines.new()
        sale_line.product = product
        sale_line.quantity = 3.0
        sale.save()
        self.assertEqual(sale.lines[0].analytic_accounts[0].account.name,
                         'Account 1.1')
        self.assertEqual(sale.lines[0].analytic_accounts[1].account.name,
                         'Account 2.2')

        # Prepare sale without warehouse when add first line and set warehouse with
        # analytic account before add second line
        sale = Sale()
        sale.party = customer
        sale.warehouse
        sale.payment_term = payment_term
        sale.invoice_method = 'order'
        sale_line = sale.lines.new()
        sale_line.product = product
        sale_line.quantity = 4.0
        sale.warehouse = warehouse2
        sale_line = sale.lines.new()
        sale_line.product = product
        sale_line.quantity = 5.0
        sale.save()
        self.assertEqual(len(sale.lines[0].analytic_accounts), 2)
        self.assertEqual(
            all(e.account == None for e in sale.lines[0].analytic_accounts),
            True)
        self.assertEqual(sale.lines[1].analytic_accounts[0].account.name,
                         'Account 1.1')
        self.assertEqual(sale.lines[1].analytic_accounts[1].account.name,
                         'Account 2.2')
