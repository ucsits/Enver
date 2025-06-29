import hashlib
import io
import math
import time
from multiformats import multihash
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader, PdfWriter
from multiformats_cid import CIDv1
import click
from web3 import Web3
import web3
import os
import tempfile
import base64
from eth_account.messages import encode_defunct
import web3.eth

@click.group()
def cli():
    """Enver CLI - Interact with Web3 from the command line."""
    pass

@cli.command()
def version():
    """Show the CLI version."""
    click.echo("enver-cli version 0.1.0")

@cli.command()
def eth_block_number():
    """Get the latest Ethereum block number (using a public endpoint)."""
    try:
        w3 = Web3(Web3.HTTPProvider("wss://ethereum-rpc.publicnode.com"))
        if w3.is_connected():
            click.echo(f"Latest block: {w3.eth.block_number}")
        else:
            click.echo("Could not connect to Ethereum node.")
    except Exception as e:
        click.echo(f"Error: {e}")
        raise click.ClickException(str(e))

def to_eth_signed_message(message: str, account: web3.Account) -> bytes:
    signature_message = encode_defunct(text=message)
    signature_bytes = account.sign_message(signature_message)
    signature_bytes = Web3.to_hex(signature_bytes.signature)
    signature_message = (
        b"\x19" +
        signature_message.version +
        signature_message.header +
        signature_message.body
    ).decode('latin-1')
    return signature_bytes, signature_message

@cli.command()
@click.argument('path_to_document', type=click.Path(exists=True))
@click.argument('page_number', required=False, default=1, type=int)
@click.argument('x', required=False, default=50, type=float)
@click.argument('y', required=False, default=50, type=float)
@click.option('--scale', default=1.0, type=float, help='Scale factor for the signature image')
@click.option('--signature', '-s', required=True, help='Path to the signature graphic file')
@click.option('--private-key', '-pk', required=True, help='Ethereum private key for signing')
@click.option('--organization', '-o', required=False, default='-', help='Organization name for the signature (optional)')
@click.option('--rpc-url', '-r', default="https://eth.drpc.org", help='Ethereum RPC URL (default: https://eth.drpc.org)')
def sign(path_to_document, page_number, x, y, scale, signature, private_key, organization, rpc_url):
    timestamp = math.floor(time.time() * 1000)
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    account = web3.Account.from_key(private_key)

    reader = PdfReader(path_to_document)
    writer = PdfWriter()

    target_page = reader.pages[page_number - 1] if page_number <= len(reader.pages) else reader.pages[-1]
    page_width = target_page.mediabox.width
    page_height = target_page.mediabox.height

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    sigImg = ImageReader(signature)
    sig_width, sig_height = sigImg.getSize()
    sig_width *= scale
    sig_height *= scale

    with open(path_to_document, "rb") as f:
        content = f.read()
        sha256_hash = hashlib.sha256(content).digest()
        mh = multihash.wrap(sha256_hash, 'sha2-256')
        ori_cid_v1 = CIDv1('dag-pb', mh)


    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=0,
    )
    signature_bytes, signed_message = to_eth_signed_message(
        (
            f"CID {ori_cid_v1} signed by {account.address}. " +
            f"Timestamp: {int(timestamp)}. " +
            f"Organization: {organization}."
        ),
        account
    )
    qr.add_data(
        signature_bytes + ' | ' + signed_message
    )
    qr.make(fit=True)
    qr_data = qr.make_image(fill_color=(0, 0, 0), back_color="transparent")

    tmp_qr_file = tempfile.NamedTemporaryFile(suffix=".png")
    qr_data.save(tmp_qr_file, format="PNG")
    qr_img = ImageReader(tmp_qr_file.name)

    can.saveState()
    can.setFillAlpha(0.1)
    can.setStrokeAlpha(0.1)
    # QR Code
    can.drawImage(qr_img, x+16, y+sig_height/4, width=64, height=64, mask='auto')
    # "Verify on Ethereum"
    # can.setFont("Helvetica", 4)
    # text = "Verify on Ethereum"
    # text_width = can.stringWidth(text, "Helvetica", 4)
    # qr_x = x + 16
    # qr_y = y + sig_height / 4
    # can.drawString(qr_x + (64 - text_width) / 2, qr_y - 5, text)
    can.restoreState()

    can.drawImage(sigImg, x, y, width=sig_width, height=sig_height, mask='auto')
    can.save()
    packet.seek(0)
    tmp_qr_file.close()
    
    signed_pdf = PdfReader(packet)
    target_page.merge_page(signed_pdf.pages[0])

    for page in reader.pages:
        writer.add_page(page)
    
    base, ext = os.path.splitext(path_to_document)
    signed_path = f"{base}_signed{ext}"
    with open(signed_path, "wb") as f:
        writer.write(f)
        print(f"Signed document saved to: {signed_path}")
    
    addr = Web3.to_checksum_address(account.address)
    print(f"Signed by\t\t: {addr}")

    print(f"Original File CID\t: {ori_cid_v1}")
    
    with open(signed_path, "rb") as f:
        content = f.read()
        sha256_hash = hashlib.sha256(content).digest()
        mh = multihash.wrap(sha256_hash, 'sha2-256')
        cid_v1_signed = CIDv1('dag-pb', mh)
        print(f"Signed File CID\t\t: {cid_v1_signed}")
    
    print(f"Signature bytes\t\t: {signature_bytes}")
    signed_message_b64 = base64.b64encode(signed_message.encode('utf-8')).decode('utf-8')
    print(f"Signed message (base64)\t: {signed_message_b64}")
    