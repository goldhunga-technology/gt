class AdminUOW:
    """Base Unit of Work class to manage administrator transactions."""

    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

    async def rollback(self):
        """Rollback the current transaction."""
        await self.session.rollback()

    async def commit(self):
        """Commit the current transaction."""
        await self.session.commit()

    async def close(self):
        """Close the session."""
        await self.session.close()
