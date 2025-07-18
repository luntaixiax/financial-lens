from pydantic import ValidationError
import typer
from typer_di import TyperDI, Depends
from src.app.model.user import UserCreate
from src.app.service.management import AdminBackupService, InitService, UserService
from src.cli.dependency.unauth_service import get_admin_backup_service, get_init_service, get_user_service

app = TyperDI(
    name='Admin CLI',
    help='Admin CLI for managing the application',
)

@app.command(help='hello')
def hello(name: str):
    print(f"Hello {name}")

@app.command(help='Initialize and create a super user')
def init(
    username: str = typer.Option(
        help='The username of the super user', 
        prompt=True, 
        confirmation_prompt=False,
    ),
    password: str = typer.Option(
        help='The password of the super user', 
        hide_input=True, 
        prompt=True, 
        confirmation_prompt=True,
    ),
    init_service: InitService = Depends(get_init_service),
    user_service: UserService = Depends(get_user_service),
):  
    # validation of parameters
    try:
        user = UserCreate(
            username=username, 
            password=password,
            is_admin=True,
        )
    except ValidationError as e:
        raise typer.BadParameter(f"Validation Error: {e}")
    
    # init db
    init_service.init_common_db()
    
    # create 1st super user
    user_service.create_user(user)

@app.command(help='Backup common data')
def backup_common_data(
    backup_id: str | None = typer.Argument(
        default=None,
        help='If provided, use the id you provide for backup', 
    ),
    backup_service: AdminBackupService = Depends(get_admin_backup_service),
):
    backup_service.backup(backup_id)
    
@app.command(help='Restore common data')
def restore_common_data(
    backup_id: str = typer.Argument(
        help='Use the id of the backup to restore', 
    ),
    backup_service: AdminBackupService = Depends(get_admin_backup_service),
):
    backup_service.restore(backup_id)

if __name__ == "__main__":
    app()