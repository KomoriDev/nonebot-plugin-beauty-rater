import base64
from io import BytesIO

import httpx
from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_waiter")
require("nonebot_plugin_alconna")
from nonebot_plugin_waiter import waiter
from nonebot_plugin_alconna.uniseg import UniMsg, UniMessage
from nonebot_plugin_alconna import Image, Match, Command, load_builtin_plugins

from .i18n import Lang, lang
from .config import Config, config
from .utils import FaceRecognition

api_key = config.api_key
secret_key = config.secret_key

if api_key == "" or secret_key == "":
    raise Exception(lang.require("rater", "error.missing_config"))


__plugin_meta__ = PluginMetadata(
    name="颜值评分",
    description="NoneBot2 颜值打分插件",
    usage="颜值评分 [图片]",
    type="application",
    homepage="https://github.com/KomoriDev/nonebot-plugin-beauty-rater",
    config=Config,
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)


load_builtin_plugins("lang")


rate = Command("rate [image:Image]").build(use_cmd_start=True)
rate.shortcut("颜值评分", {"command": "rate", "fuzzy": True, "prefix": True})
rate.shortcut("颜值打分", {"command": "rate", "fuzzy": True, "prefix": True})


@rate.handle()
async def _(image: Match[Image]):
    if image.available:
        img_url = image.result.url
        if img_url is None:
            await UniMessage.i18n(Lang.rater.error_no_image_found).send(at_sender=True)
            return

    else:
        await UniMessage.i18n(Lang.rater.prompt).send(at_sender=True)

        @waiter(waits=["message"], keep_session=True)
        async def receive(msg: UniMsg):
            return msg

        resp = await receive.wait(timeout=30)
        if resp is None:
            await UniMessage.i18n(Lang.rater.error_timeout).send(at_sender=True)
            return
        if not resp.only(Image):
            await UniMessage.i18n(Lang.rater.error_invalid_input).send(at_sender=True)
            return

        imgs = resp[Image]
        urls = [i.url for i in imgs if i.url]
        img_url = urls[0]

    async with httpx.AsyncClient() as client:
        res = await client.get(img_url)

    img = base64.b64encode(res.content).decode()

    faces = FaceRecognition(img, api_key, secret_key)
    result = await faces.face_beauty()

    if result["error_msg"] == "pic not has face":
        await UniMessage.i18n(Lang.rater.error_no_face_found).send(at_sender=True)
    elif result["error_msg"] == "image size is too large":
        await UniMessage.i18n(Lang.rater.error_too_large).send(at_sender=True)

    faces_gender = []
    faces_pos = []
    faces_beauty = []

    for face in result["result"]["face_list"]:
        faces_gender.append(
            lang.require("rater", "male")
            if face["gender"]["type"] == "male"
            else lang.require("rater", "female")
        )
        faces_pos.append(face["location"])
        faces_beauty.append(face["beauty"])

    pic = res.content
    pic_bytes_stream = BytesIO(pic)
    buf = BytesIO()
    await faces.draw_face_rects(pic_bytes_stream, buf, faces_pos)

    msg = "\n".join(
        [
            Lang.rater.result(count=i + 1, gender=gender, score=f"{beauty}/100")
            for i, (gender, beauty) in enumerate(zip(faces_gender, faces_beauty))
        ]
    )
    await UniMessage(msg).send(at_sender=True)

    pic_bytes_stream.close()
    buf.close()

    await rate.finish()
