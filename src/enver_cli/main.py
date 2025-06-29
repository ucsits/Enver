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
import PIL
from PIL import Image, ImageDraw
from qrcode.image.pil import PilImage
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

def draw_snake(can, ori_cid_v1, account, timestamp, organization, sig_height, x, y):
    can.saveState()
    can.setFillAlpha(0.35)
    can.setStrokeAlpha(0.35)
    can.setFont("Courier", 1.5)
    snake_text = (
        f" {ori_cid_v1} | "
        f"{account.address} | "
        f"{int(timestamp)} | "
        f"{organization} | "
        "Verify on Ethereum "
    )
    qr_x = x + 16
    qr_y = y + sig_height / 4
    qr_size = 64
    margin = 2  # distance from QR code
    corner_radius = 3

    # Calculate total perimeter (4 sides + 4 quarter circles)
    straight = 4 * (qr_size + 2 * margin - 2 * corner_radius)
    arc = 2 * math.pi * corner_radius  # full circle, but we use 4 quarter circles
    perimeter = straight + arc

    snake_text_full = snake_text
    
    while can.stringWidth(snake_text_full, "Courier", 1.5) < perimeter:
        snake_text_full += "*"

    char_idx = 0
    char_width = 1.5

    # Helper to draw text along a straight line
    def draw_text_line(start_x, start_y, dx, dy, length, angle):
        nonlocal char_idx
        steps = int(length // char_width)
        can.saveState()
        can.translate(start_x, start_y)
        can.rotate(angle)
        text_obj = can.beginText()
        text_obj.setFont("Courier", 1.5)
        text_obj.setTextOrigin(0, 0)
        for _ in range(steps):
            if char_idx >= len(snake_text_full):
                break
            char = snake_text_full[char_idx]
            text_obj.textOut(char)
            text_obj.moveCursor(char_width, 0)
            char_idx += 1
        can.drawText(text_obj)
        can.restoreState()

    # Helper to draw text along a quarter circle (rounded corner)
    def draw_text_arc(center_x, center_y, radius, start_angle, extent):
        nonlocal char_idx
        arc_length = abs(math.radians(extent) * radius)
        steps = int(arc_length // char_width)
        for i in range(steps):
            if char_idx >= len(snake_text_full):
                break
            angle = math.radians(start_angle + (extent / steps) * i)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            can.saveState()
            can.translate(x, y)
            can.rotate(start_angle + (extent / steps) * i + 90)
            can.setFont("Courier", 1.5)
            can.drawString(0, 0, snake_text_full[char_idx])
            can.restoreState()
            char_idx += 1

    # Bottom side
    draw_text_line(
        qr_x - margin + corner_radius,
        qr_y - margin,
        1, 0,
        qr_size + 2 * margin - 2 * corner_radius,
        0
    )
    # Bottom-right corner (quarter circle)
    draw_text_arc(
        qr_x + qr_size + margin - corner_radius,
        qr_y - margin + corner_radius,
        corner_radius,
        270, 90
    )
    # Right side
    draw_text_line(
        qr_x + qr_size + margin,
        qr_y - margin + corner_radius,
        0, 1,
        qr_size + 2 * margin - 2 * corner_radius,
        90
    )
    # Top-right corner
    draw_text_arc(
        qr_x + qr_size + margin - corner_radius,
        qr_y + qr_size + margin - corner_radius,
        corner_radius,
        0, 90
    )
    # Top side
    draw_text_line(
        qr_x + qr_size + margin - corner_radius,
        qr_y + qr_size + margin,
        -1, 0,
        qr_size + 2 * margin - 2 * corner_radius,
        180
    )
    # Top-left corner
    draw_text_arc(
        qr_x - margin + corner_radius,
        qr_y + qr_size + margin - corner_radius,
        corner_radius,
        90, 90
    )
    # Left side
    draw_text_line(
        qr_x - margin,
        qr_y + qr_size + margin - corner_radius,
        0, -1,
        qr_size + 2 * margin - 2 * corner_radius,
        270
    )
    # Bottom-left corner
    draw_text_arc(
        qr_x - margin + corner_radius,
        qr_y - margin + corner_radius,
        corner_radius,
        180, 90
    )

    can.restoreState()

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
    # Use PilImage factory for compatibility and set fill/back color as RGB tuples
    qr_data = qr.make_image(
        image_factory=PilImage,
        fill_color=(0, 0, 0),
        back_color=(255, 255, 255)
    ).convert("RGBA")

    # Make QR code rounded with 2 unit corner radius
    qr_px_size = qr_data.size[0]
    corner_radius = 2 * qr.box_size  # 2 units in pixels

    # Create rounded mask
    mask = Image.new("L", qr_data.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        [(0, 0), (qr_px_size, qr_px_size)],
        radius=corner_radius,
        fill=255
    )
    qr_rounded = qr_data.copy()
    qr_rounded.putalpha(mask)

    tmp_qr_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    qr_rounded.save(tmp_qr_file, format="PNG")
    qr_img = ImageReader(tmp_qr_file.name)

    can.saveState()
    can.rotate(5)
    can.translate(20, -35)
    can.setFillAlpha(0.1)
    can.setStrokeAlpha(0.1)
    # QR Code
    can.drawImage(qr_img, x+16, y+sig_height/4, width=64, height=64, mask='auto')
    
    draw_snake(can, ori_cid_v1, account, timestamp, organization, sig_height, x, y)
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
    