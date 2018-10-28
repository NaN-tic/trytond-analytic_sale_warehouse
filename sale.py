# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['Location', 'Sale', 'SaleLine']


class Location(metaclass=PoolMeta):
    __name__ = 'stock.location'

    @classmethod
    def enabled_location_types(cls):
        # Show companies field (with analytic accounts configuration) in
        # warehouse locations
        enabled_types = super(Location, cls).enabled_location_types()
        if 'warehouse' not in enabled_types:
            enabled_types.append('warehouse')
        return enabled_types


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        cls.lines.context['warehouse'] = Eval('warehouse')


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    @classmethod
    def default_analytic_accounts(cls):
        pool = Pool()
        Location = pool.get('stock.location')
        Sale = pool.get('sale.sale')

        entries = super(SaleLine, cls).default_analytic_accounts()

        company_id = Sale.default_company()
        warehouse = Transaction().context.get('warehouse')
        if warehouse:
            root2account = {}
            for location_company in Location(warehouse).companies:
                if location_company.company.id != company_id:
                    continue
                for entry in location_company.analytic_accounts:
                    root2account[entry.root.id] = entry.account.id
            if root2account:
                for entry in entries:
                    if entry['root'] in root2account:
                        entry['account'] = root2account[entry['root']]
        return entries
