import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


MAX_NFE_XML_LENGTH = 2_000_000
MAX_NFE_ITEMS = 990


@dataclass(frozen=True)
class NfeItem:
    code: str
    barcode: str | None
    name: str
    ncm: str | None
    cst: str | None
    quantity: Decimal
    unit_cost: Decimal


@dataclass(frozen=True)
class NfeInvoice:
    access_key: str
    number: str
    supplier_name: str
    supplier_document: str
    total: Decimal
    items: list[NfeItem]


def _child(element: ET.Element, name: str) -> ET.Element | None:
    return next(
        (node for node in element if node.tag.rsplit("}", 1)[-1] == name),
        None,
    )


def _text(element: ET.Element | None, name: str) -> str:
    child = _child(element, name) if element is not None else None
    return (child.text or "").strip() if child is not None else ""


def _decimal(value: str, field: str) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"O campo {field} da NF-e é inválido.") from error
    if not number.is_finite() or number < 0:
        raise ValueError(f"O campo {field} da NF-e é inválido.")
    return number


def parse_nfe(xml: str) -> NfeInvoice:
    if len(xml) > MAX_NFE_XML_LENGTH:
        raise ValueError("O arquivo XML da NF-e excede o limite de 2 MB.")
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", xml, flags=re.IGNORECASE):
        raise ValueError("O XML da NF-e não pode conter declarações DTD ou entidades.")

    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        raise ValueError("O arquivo não contém um XML válido.") from error

    info = next(
        (
            element
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "infNFe"
        ),
        None,
    )
    if info is None:
        raise ValueError("O XML não contém uma NF-e válida.")

    access_key = info.attrib.get("Id", "").removeprefix("NFe")
    if not re.fullmatch(r"\d{44}", access_key):
        raise ValueError("A chave de acesso da NF-e deve conter 44 dígitos.")

    ide = _child(info, "ide")
    number = _text(ide, "nNF")
    if not number:
        raise ValueError("A NF-e não contém o número da nota.")

    issuer = _child(info, "emit")
    supplier_name = _text(issuer, "xNome")
    supplier_document = _text(issuer, "CNPJ") or _text(issuer, "CPF")
    if not supplier_name or not re.fullmatch(r"\d{11}|\d{14}", supplier_document):
        raise ValueError("O XML não contém nome e CPF/CNPJ válidos do fornecedor.")

    items: list[NfeItem] = []
    details = [
        element
        for element in info.iter()
        if element.tag.rsplit("}", 1)[-1] == "det"
    ]
    if not details or len(details) > MAX_NFE_ITEMS:
        raise ValueError("A NF-e deve conter entre 1 e 990 itens.")

    for detail in details:
        product = _child(detail, "prod")
        code = _text(product, "cProd")
        name = _text(product, "xProd")
        if not code or not name:
            raise ValueError("Um item da NF-e está sem código ou descrição.")

        quantity = _decimal(_text(product, "qCom"), "qCom")
        if quantity <= 0 or quantity > Decimal("99999999.999"):
            raise ValueError("A quantidade de um item da NF-e está fora do limite.")
        try:
            has_supported_precision = quantity.quantize(Decimal("0.001")) == quantity
        except InvalidOperation:
            has_supported_precision = False
        if not has_supported_precision:
            raise ValueError(
                "A quantidade de um item tem mais casas decimais do que o estoque suporta."
            )
        price_text = _text(product, "vUnCom")
        if price_text:
            unit_cost = _decimal(price_text, "vUnCom")
        else:
            line_value = _decimal(_text(product, "vProd"), "vProd")
            unit_cost = line_value / quantity
        if unit_cost > Decimal("9999999999.99"):
            raise ValueError("O custo unitário de um item excede o limite suportado.")

        barcode = _text(product, "cEAN")
        if not re.fullmatch(r"(?:\d{8}|\d{12,14})", barcode):
            barcode = _text(product, "cEANTrib")
        if not re.fullmatch(r"(?:\d{8}|\d{12,14})", barcode):
            barcode = None
        ncm = _text(product, "NCM")
        if not re.fullmatch(r"\d{8}", ncm):
            ncm = None

        tax = _child(detail, "imposto")
        cst = None
        if tax is not None:
            for element in tax.iter():
                if element.tag.rsplit("}", 1)[-1] in {"CST", "CSOSN"}:
                    value = (element.text or "").strip()
                    if re.fullmatch(r"\d{2,3}", value):
                        cst = value
                        break

        items.append(
            NfeItem(
                code=code,
                barcode=barcode,
                name=name[:160],
                ncm=ncm,
                cst=cst,
                quantity=quantity,
                unit_cost=unit_cost,
            )
        )

    total_text = _text(
        _child(_child(info, "total"), "ICMSTot"),
        "vNF",
    )
    if not total_text:
        raise ValueError("A NF-e não contém o valor total da nota.")
    total = _decimal(total_text, "vNF")
    if total <= 0:
        raise ValueError("O valor total da NF-e deve ser maior que zero.")
    if total > Decimal("999999999999.99"):
        raise ValueError("O valor total da NF-e excede o limite suportado.")

    return NfeInvoice(
        access_key=access_key,
        number=number[:20],
        supplier_name=supplier_name[:160],
        supplier_document=supplier_document,
        total=total,
        items=items,
    )
