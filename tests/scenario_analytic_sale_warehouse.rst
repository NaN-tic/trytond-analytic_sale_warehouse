================================
Analytic Sale Warehouse Scenario
================================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()


Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True


Install analytic_sale_warehouse::

    >>> Module = Model.get('ir.module.module')
    >>> sale_module, = Module.find([('name', '=', 'analytic_sale_warehouse')])
    >>> Module.install([sale_module.id], config.context)
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')


Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='U.S. Dollar', symbol='$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[3, 3, 0]',
    ...         mon_decimal_point='.', mon_thousands_sep=',')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find([])


Reload the context::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')
    >>> config._context = User.get_preferences(True, config.context)


Create sale user::

    >>> sale_user = User()
    >>> sale_user.name = 'Sale'
    >>> sale_user.login = 'sale'
    >>> sale_user.main_company = company
    >>> sale_group, = Group.find([('name', '=', 'Sales')])
    >>> sale_user.groups.append(sale_group)
    >>> sale_user.save()


Create chart of accounts::

    >>> AccountTemplate = Model.get('account.account.template')
    >>> Account = Model.get('account.account')
    >>> Journal = Model.get('account.journal')
    >>> account_template, = AccountTemplate.find([('parent', '=', None)])
    >>> create_chart = Wizard('account.create_chart')
    >>> create_chart.execute('account')
    >>> create_chart.form.account_template = account_template
    >>> create_chart.form.company = company
    >>> create_chart.execute('create_account')
    >>> receivable, = Account.find([
    ...         ('kind', '=', 'receivable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> payable, = Account.find([
    ...         ('kind', '=', 'payable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> revenue, = Account.find([
    ...         ('kind', '=', 'revenue'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> expense, = Account.find([
    ...         ('kind', '=', 'expense'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')
    >>> cash, = Account.find([
    ...         ('kind', '=', 'other'),
    ...         ('name', '=', 'Main Cash'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> cash_journal.credit_account = cash
    >>> cash_journal.debit_account = cash
    >>> cash_journal.save()


Create an analytic hierarchy::

    >>> AnalyticAccount = Model.get('analytic_account.account')
    >>> root1 = AnalyticAccount(name='Root 1', type='root')
    >>> root1.save()
    >>> analytic_account = AnalyticAccount(name='Account 1.1', root=root1)
    >>> root1.childs.append(analytic_account)
    >>> analytic_account = AnalyticAccount(name='Account 1.2', root=root1)
    >>> root1.childs.append(analytic_account)
    >>> root1.save()


Create a second analytic hierarchy::

    >>> root2 = AnalyticAccount(name='Root 1', type='root')
    >>> root2.save()
    >>> analytic_account = AnalyticAccount(name='Account 2.1', root=root2)
    >>> root2.childs.append(analytic_account)
    >>> analytic_account = AnalyticAccount(name='Account 2.2', root=root2)
    >>> root2.childs.append(analytic_account)
    >>> root2.save()


Create parties::

    >>> Party = Model.get('party.party')
    >>> customer = Party(name='Customer')
    >>> customer.save()


Create category::

    >>> ProductCategory = Model.get('product.category')
    >>> category = ProductCategory(name='Category')
    >>> category.save()


Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.category = category
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('10')
    >>> template.cost_price = Decimal('5')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> product.template = template
    >>> product.save()


Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> PaymentTermLine = Model.get('account.invoice.payment_term.line')
    >>> payment_term = PaymentTerm(name='Direct')
    >>> payment_term_line = PaymentTermLine(type='remainder', days=0)
    >>> payment_term.lines.append(payment_term_line)
    >>> payment_term.save()


Create a warehouse with assigned analytic accounts::

    >>> Location = Model.get('stock.location')
    >>> input_loc2 = Location(name='Input 2')
    >>> input_loc2.save()
    >>> output_loc2 = Location(name='Output 2')
    >>> output_loc2.save()
    >>> storage_loc2 = Location(name='Storage 2')
    >>> storage_loc2.save()
    >>> warehouse2, = Location.create([{
    ...             'name': 'Warehouse 2',
    ...             'type': 'warehouse',
    ...             'input_location': input_loc2.id,
    ...             'output_location': output_loc2.id,
    ...             'storage_location': storage_loc2.id,
    ...             'analytic_account_%s' % root1.id: root1.childs[0].id,
    ...             'analytic_account_%s' % root2.id: root2.childs[-1].id,
    ...             }], config.context)
    >>> warehouse2 = Location(warehouse2)
    >>> warehouse2.analytic_accounts.accounts[0].name
    u'Account 1.1'
    >>> warehouse2.analytic_accounts.accounts[1].name
    u'Account 2.2'


Prepare sale to warehouse without analytic accounts::

    >>> config.user = sale_user.id
    >>> Sale = Model.get('sale.sale')
    >>> warehouse1, = Location.find([('code', '=', 'WH')])
    >>> sale = Sale()
    >>> sale.party = customer
    >>> sale.warehouse = warehouse1
    >>> sale.payment_term = payment_term
    >>> sale.invoice_method = 'order'
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product
    >>> sale_line.quantity = 2.0
    >>> sale.save()
    >>> len(sale.lines[0].analytic_accounts.accounts)
    0


Prepare sale to warehouse with analytic accounts::

    >>> sale = Sale()
    >>> sale.party = customer
    >>> sale.warehouse = warehouse2
    >>> sale.payment_term = payment_term
    >>> sale.invoice_method = 'order'
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product
    >>> sale_line.quantity = 3.0
    >>> sale.save()
    >>> sale.lines[0].analytic_accounts.accounts[0].name
    u'Account 1.1'
    >>> sale.lines[0].analytic_accounts.accounts[1].name
    u'Account 2.2'


Prepare sale without warehouse when add first line and set warehouse with
analytic account before add second line::

    >>> sale = Sale()
    >>> sale.party = customer
    >>> sale.warehouse
    >>> sale.payment_term = payment_term
    >>> sale.invoice_method = 'order'
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product
    >>> sale_line.quantity = 4.0
    >>> sale.warehouse = warehouse2
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product
    >>> sale_line.quantity = 5.0
    >>> sale.save()
    >>> len(sale.lines[0].analytic_accounts.accounts)
    0
    >>> sale.lines[1].analytic_accounts.accounts[0].name
    u'Account 1.1'
    >>> sale.lines[1].analytic_accounts.accounts[1].name
    u'Account 2.2'
