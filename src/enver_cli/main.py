import click
from web3 import Web3

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
