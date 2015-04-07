# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['Sale', 'SaleLine']
__metaclass__ = PoolMeta


class Sale:
    __name__ = 'sale.sale'

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        cls.lines.context['warehouse'] = Eval('warehouse')


class SaleLine:
    __name__ = 'sale.line'

    @classmethod
    def default_get(cls, fields, with_rec_name=True):
        pool = Pool()
        Location = pool.get('stock.location')

        warehouse = Transaction().context.get('warehouse')
        if warehouse:
            warehouse = Location(warehouse)

        default_values = super(SaleLine, cls).default_get(fields,
            with_rec_name=with_rec_name)
        if (not warehouse or not warehouse.analytic_accounts
                or not warehouse.analytic_accounts.accounts):
            return default_values

        account_by_root = dict((a.root.id, a)
            for a in warehouse.analytic_accounts.accounts)
        analytic_account_fields = [f for f in fields
            if f.startswith('analytic_account_')]
        for fname in analytic_account_fields:
            root_id = int(fname[17:])
            if root_id in account_by_root:
                default_values[fname] = account_by_root[root_id].id
                if with_rec_name:
                    default_values[fname + '.rec_name'] = (
                        account_by_root[root_id].rec_name)
        return default_values
