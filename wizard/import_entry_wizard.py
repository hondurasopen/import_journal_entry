# -*- encoding: utf-8 -*-
from odoo import fields, models, exceptions, api, _
import base64
import csv
from io import BytesIO
from io import StringIO
import io
from datetime import datetime


class ImportJournalEntry(models.TransientModel):
    _name = 'import.journal.entry.wizard'


    data = fields.Binary('File', required=True)
    name = fields.Char('Filename')
    delimeter = fields.Char('Delimeter', default=',', help='Por defecto el delimitador es","')

 
    def action_import(self):
        """Load Inventory data from the CSV file."""
        ctx = self._context
        account_obj = self.env["account.account"]
        import_obj = self.env['import.journal.entries']
        import_line_obj = self.env['import.journal.entries.detail']
        if 'active_id' in ctx:
            import_id = import_obj.browse(ctx['active_id'])
        if not self.data:
            raise exceptions.Warning(_("Necesitas seleccionar un archivo!"))
        # Decode the file data
        data = base64.b64decode(self.data).decode('utf-8')
        file_input = StringIO(data)
        file_input.seek(0)
        reader_info = []
        if self.delimeter:
            delimeter = str(self.delimeter)
        else:
            delimeter = ','
        reader = csv.reader(file_input, delimiter=delimeter,
                            lineterminator='\r\n')
        try:
            reader_info.extend(reader)
        except Exception:
            raise exceptions.Warning(_("Archivo no valido"))
        keys = reader_info[0]
        # check if keys exist
        if not isinstance(keys, list) or ('cuenta' not in keys):
            raise exceptions.Warning(_("No se encuentran 'cuentas' contable en el archivo"))
        del reader_info[0]
        values = {}
        actual_date = fields.Date.today()
        for i in range(len(reader_info)):
            val = {}
            field = reader_info[i]
            values = dict(zip(keys, field))
            account = False
            if 'cuenta' in values and values['cuenta']:
                account_id = account_obj.search([('code', '=', values['cuenta'])])  
                if account_id:
                    account = account_id[0]
                else:
                    account = account_id

            val["description"] = values["descripcion"]
            val["bank_transaction"] = values["transaccion_banco"]
            val["document_number"] = values["num_documento"]
            val["beneficiary"] = values["beneficiario"]
            val["document_date"] = datetime.strptime(values["fecha"] , "%d-%m-%Y")
            val["verified_document"] = values["documento_fisico"]
            val['account_id'] = account.id
            val['parent_id'] = import_id.id
            val['debit'] = values['debito']
            val['credit'] = values['credito']
            val['processed'] = False
            validate = import_line_obj.create(val)
            if validate:
                if validate.account_id:
                    validate.is_ok = True