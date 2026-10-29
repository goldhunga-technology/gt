from collections.abc import AsyncGenerator, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from gt.admin.models import AdminModel, TAdmin, create_admin_model
from gt.admin.routers import create_admins_router
from gt.admin.services import AdminServiceRegistry
from gt.auth.events import event_bus


class Admin:
    """
    This class is responsible for wiring administrator models, services and
    routers onto the application.
    """

    def __init__(
        self,
        *,
        base: type[DeclarativeBase],
        session_factory: async_sessionmaker[AsyncSession],
        admin_model: type[TAdmin] | None = None,
        current_admin: Callable | None = None,
    ):
        """
        Initializes the Admin class.

        Args:
            base: The declarative base class (SQLAlchemy or SQLModel).
            session_factory: The application's async session factory.
            admin_model: An optional custom admin model base.
            current_admin: A FastAPI dependency that resolves the current
                authenticated administrator. It is required to protect the
                admin list endpoint; when omitted, calling that endpoint raises
                ``ADMIN_AUTH_NOT_CONFIGURED``.
        """
        self.session_factory = session_factory

        ## models
        self.admin_model = create_admin_model(
            base=base,
            model=admin_model or AdminModel,
        )

        ## dependencies
        self.current_admin = current_admin

        ## event bus
        self.event_bus = event_bus

    def init_app(self, app, prefix: str | None = None):
        """
        Initializes the FastAPI application with administrator routes.

        Args:
            app: The FastAPI application.
            prefix: An optional path prefix prepended to every admin route.
        """
        self._register_routers(app, prefix=prefix)
        self._register_exceptions(app)

    def on(self, event_type: type):
        """
        Registers an event handler for a specific event type.

        :param event_type: The type of the event to listen for.
        """

        def decorator(handler):
            self.event_bus.register(event_type, handler)
            return handler

        return decorator

    def get_services(self, session: AsyncSession) -> AdminServiceRegistry:
        """
        Builds a per-session AdminServiceRegistry with the admin model pre-wired.

        Access the service as an attribute of the returned registry, e.g.
        ``admin.get_services(session).admin``.
        """
        return AdminServiceRegistry(
            session=session,
            admin_model=self.admin_model,
        )

    async def get_db_session(self) -> AsyncGenerator[AsyncSession]:
        """
        Provides a database session for use in the application.
        """
        async with self.session_factory() as session:
            yield session

    def _register_routers(self, app, prefix: str | None = None):
        """
        Registers administrator-related routers to the FastAPI application.
        """
        routers = create_admins_router(admin=self)
        if prefix:
            app.include_router(routers, prefix=prefix)
        else:
            app.include_router(routers)

    def _register_exceptions(self, app):
        """
        Registers custom exception handlers to the FastAPI application.
        """
        from gt.exceptions import add_exceptions_handler

        add_exceptions_handler(app)
