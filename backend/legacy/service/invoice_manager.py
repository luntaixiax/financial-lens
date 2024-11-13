from typing import List, Tuple, Dict
from decimal import Decimal
from pathlib import Path
from itertools import cycle
from datetime import datetime
from borb.pdf.document.document import Document
from borb.pdf.page.page import Page
from borb.pdf.canvas.layout.page_layout.multi_column_layout import SingleColumnLayout
from borb.pdf.canvas.layout.image.image import Image
from borb.pdf.canvas.layout.table.fixed_column_width_table import FixedColumnWidthTable
from borb.pdf.canvas.layout.table.table import TableCell
from borb.pdf.canvas.layout.text.paragraph import Paragraph
from borb.pdf.canvas.layout.layout_element import Alignment
from borb.pdf.canvas.color.color import HexColor, X11Color
from borb.pdf.pdf import PDF

from legacy.model.invoice import Invoice, InvoiceItem
from legacy.dao.invoice import invoiceDao
from legacy.dao.entity import entityDao
from legacy.utils.tools import get_abs_img_path
        
class InvoiceManager:
    
    @classmethod
    def create(cls, invoice: Invoice):
        invoiceDao.add(invoice)
        
    @classmethod
    def update(cls, invoice: Invoice):
        invoiceDao.update(invoice)
        
    @classmethod
    def delete(cls,invoice_id: str):
        invoiceDao.remove(invoice_id=invoice_id)
        
    @classmethod
    def get(cls, invoice_id: str) -> Invoice:
        return invoiceDao.get(invoice_id=invoice_id)
    
    @classmethod
    def make_pdf_invoice(
        cls,
        invoice: Invoice,
        size: Tuple = (650, 800)
    ):
        # initialize pdf
        pdf = Document()
        page = Page(
            width = Decimal(size[0]),
            height = Decimal(size[1])
        )
        pdf.add_page(page)
        page_layout = SingleColumnLayout(page)
        
        # get provider
        entity_id_provider = invoice.entity_id_provider
        entity_provider = entityDao.get(entity_id = entity_id_provider)
        entity_id_payer = invoice.entity_id_payer
        entity_payer = entityDao.get(entity_id = entity_id_payer)
        
        # see if it has avatar
        if entity_provider.avatar is not None:
            # leave space for logo
            page_layout.vertical_margin = page.get_page_info().get_height() * Decimal(0.02)
            # add logo
            page_layout.add(
                Image(
                    image = Path(entityDao.get_avatar_abs_path(entity_id=entity_id_provider)),
                    width = Decimal(64),
                    height = Decimal(64)
                )
            )
        
        ###### add invoice information  ##########
        table_info = FixedColumnWidthTable(
            number_of_rows = 2, 
            number_of_columns = 5
        ) # grid layout
        
        # add invoice number
        table_info.add(Paragraph(
            "Invoice #:", 
            font="Helvetica-Bold", 
            horizontal_alignment=Alignment.LEFT
        ))
        table_info.add(Paragraph(
            invoice.invoice_id
        ))
        table_info.add(Paragraph(" "))
        table_info.add(Paragraph(" "))
        table_info.add(Paragraph(" "))
        # add invoice date
        table_info.add(Paragraph(
            "Invoice Date:", 
            font="Helvetica-Bold", 
            horizontal_alignment=Alignment.LEFT
        ))
        table_info.add(Paragraph(
            invoice.invoice_dt.strftime("%Y-%m-%d")
        ))
        table_info.add(Paragraph(" "))
        table_info.add(Paragraph(" "))
        table_info.add(Paragraph(" "))
        
        table_info.set_padding_on_all_cells(
            Decimal(2), 
            Decimal(2), 
            Decimal(2), 
            Decimal(2)
        )  
        table_info.no_borders()  
        
        page_layout.add(table_info)
        page_layout.add(Paragraph(" "))
        
        ###### add provider/receiver info  ##########
        table_pr = FixedColumnWidthTable(
            number_of_rows = 5, 
            number_of_columns = 2
        ) # grid layout
        
        table_pr.add(  
            Paragraph(  
                "BILL FROM",  
                background_color=HexColor("#702307"),  
                font_color=X11Color("White"), 
                padding_top=Decimal(3),
                padding_bottom=Decimal(2),
                padding_left=Decimal(2),
                padding_right=Decimal(2),
            )  
        )  
        table_pr.add(  
            Paragraph(  
                "BILL TO",  
                background_color=HexColor("#263238"),  
                font_color=X11Color("White"),
                padding_top=Decimal(3),
                padding_bottom=Decimal(2),
                padding_left=Decimal(2),
                padding_right=Decimal(2),
            )  
        )  
        # add bill from company name
        table_pr.add(Paragraph(
            entity_provider.name, # company name
            font="Helvetica-Bold", 
            font_color=HexColor("#702307"),
            font_size=Decimal(14)
        ))
        # add bill to company name
        table_pr.add(Paragraph(
            entity_payer.name, # company name
            font="Helvetica-Bold", 
            font_color=HexColor("#263238"),
            font_size=Decimal(14)
        ))
        
        
        # add street line from company name
        table_pr.add(Paragraph(
            entity_provider.address.address_line 
        ))
        # add street line to company name
        table_pr.add(Paragraph(
            entity_payer.address.address_line 
        ))
        
        
        # add city, state, country from company name
        table_pr.add(Paragraph(
            entity_provider.address.post_code_line 
        ))
        # add city, state, country to company name
        table_pr.add(Paragraph(
            entity_payer.address.post_code_line 
        ))
        
        # add email from company name
        table_pr.add(Paragraph(
            entity_provider.email
        ))
        # add email to company name
        table_pr.add(Paragraph(
            entity_payer.email
        ))
        
        table_pr.set_padding_on_all_cells(
            Decimal(2), 
            Decimal(2), 
            Decimal(2), 
            Decimal(2)
        )  
        table_pr.no_borders()
        
        page_layout.add(table_pr)
        page_layout.add(Paragraph(" "))
        
        ###### add itemnized description  ##########
        items = invoice.items
        curreny = invoice.currency.name
        
        table_001 = FixedColumnWidthTable(
            number_of_rows=len(items) + 3, 
            number_of_columns=4
        )
        # add header
        for h in ["DESCRIPTION", "QTY", "UNIT PRICE", "AMOUNT"]:  
            table_001.add(  
                TableCell(  
                    Paragraph(h, font_color=X11Color("White")),  
                    background_color=HexColor("#263238"),  
                )  
            )
        # add items
        colors = cycle([HexColor("#BBBBBB"), HexColor("#FFFFFF")])
        for item in items:
            c = next(colors)
            table_001.add(TableCell(
                Paragraph(item.desc), 
                background_color=c
            ))
            table_001.add(TableCell(
                Paragraph(f"{item.quantity}"), 
                background_color=c
            ))
            table_001.add(TableCell(
                Paragraph(f"{curreny} {item.unit_price:,.2f}"), 
                background_color=c
            ))
            table_001.add(TableCell(
                Paragraph(f"{curreny} {item.subtotal:,.2f}"), 
                background_color=c
            ))
            
        # Optionally add some empty rows to have a fixed number of rows for styling purposes
        for _ in range(2):  
            c = next(colors)
            for _ in range(0, 4):  
                table_001.add(TableCell(
                    Paragraph(""), 
                    background_color=c
                ))
        
        table_001.set_padding_on_all_cells(
            Decimal(2), 
            Decimal(2), 
            Decimal(2), 
            Decimal(2)
        )  
        table_001.no_borders()  
        
        page_layout.add(table_001)
        
        ###### add note  ##########
        page_layout.add(Paragraph(
            f"Note: {invoice.note}",
            font_color = HexColor("#848687")
        ))
        page_layout.add(Paragraph(" "))
        
        ###### add subtotal  ##########
        table_002 = FixedColumnWidthTable(
            number_of_rows=5, 
            number_of_columns=5
        )
        table_002.add(TableCell(
            Paragraph("Subtotal", font="Helvetica-Bold", horizontal_alignment=Alignment.RIGHT,), 
            column_span=4
        ))  
        table_002.add(TableCell(
            Paragraph(f"{curreny} {invoice.subtotal:,.2f}", horizontal_alignment=Alignment.RIGHT)
        ))  
        table_002.add(TableCell(
            Paragraph("Discounts", font="Helvetica-Bold", horizontal_alignment=Alignment.RIGHT,),
            column_span=4
        ))  
        table_002.add(TableCell(
            Paragraph(f"{curreny} ({invoice.discount:,.2f})", font_color = HexColor("#702307"), horizontal_alignment=Alignment.RIGHT)
        ))  
        table_002.add(TableCell(
            Paragraph("Tax", font="Helvetica-Bold", horizontal_alignment=Alignment.RIGHT), 
            column_span=4
        ))  
        table_002.add(TableCell(
            Paragraph(f"{curreny} {invoice.tax:,.2f}", horizontal_alignment=Alignment.RIGHT)
        ))  
        table_002.add(TableCell(
            Paragraph("Shipping/Process", font="Helvetica-Bold", horizontal_alignment=Alignment.RIGHT), 
            column_span=4
        ))  
        table_002.add(TableCell(
            Paragraph(f"{curreny} {invoice.shipping:,.2f}", horizontal_alignment=Alignment.RIGHT)
        ))  
        table_002.add(TableCell(
            Paragraph("Total", font="Helvetica-Bold", border_bottom = True, horizontal_alignment=Alignment.RIGHT), 
            column_span=4
        ))  
        table_002.add(TableCell(
            Paragraph(f"{curreny} {invoice.total:,.2f}", border_bottom = True, font="Helvetica-Bold", horizontal_alignment=Alignment.RIGHT)
        ))
        
        table_002.set_padding_on_all_cells(
            Decimal(2), 
            Decimal(2), 
            Decimal(2), 
            Decimal(2)
        )  
        table_002.no_borders()  
        
        page_layout.add(table_002)
        
        filename = get_abs_img_path(
            img_name = f'{invoice.invoice_id}.pdf',
            sector = 'invoices'
        )
        with open(filename, "wb") as obj:
            PDF.dumps(obj, pdf)
            
            
if __name__ == '__main__':
    from model.enums import CurType
    
    i = Invoice(
        invoice_id='i-123',
        invoice_dt=datetime(2023, 10, 19, 9, 0, 0),
        entity_id_provider='e-41ac6',
        entity_id_payer='e-f452e',
        currency=CurType.CAD,
        items = [
            InvoiceItem(
                item_id = 1,
                desc = 'Lecture and Coaching',
                unit_price = 50,
                quantity = 12.5,
                tax = 0
            ),
            InvoiceItem(
                item_id = 2,
                desc = 'Capstone Project',
                unit_price = 500,
                quantity = 1,
                tax = 0
            )
        ],
        note = 'HST not charged, courses delivered online'
    )
    print(i)
    
    InvoiceManager.make_pdf_invoice(invoice=i)