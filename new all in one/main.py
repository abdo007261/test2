import asyncio
from fivem_r_g_en_bot import main as e5nm
from fivem_r_g_indonisia_bot import main as indo5nm
from fivem_r_g_vitname_bot import main as vit5nm
from fivem_r_g_Jabanise_bot import main as jab5nm


async def main():
    await asyncio.gather(e5nm(), indo5nm(), vit5nm(), jab5nm())


if __name__ == "__main__":
    asyncio.run(main())
