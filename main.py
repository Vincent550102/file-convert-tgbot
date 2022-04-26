from cgitb import text
import os
from telegram.ext import Filters, Updater, CommandHandler, CallbackQueryHandler, MessageHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from text import help_text, recieve_text, convert_type_text, converting_text, convert_success_text
import cloudconvert
load_dotenv()


class Convert():
    def __init__(self):
        CLOUDCONVERT_API_KEY = os.getenv("CLOUDCONVERT_API_KEY")
        cloudconvert.configure(api_key=CLOUDCONVERT_API_KEY)

    def create_job(self, convert_format):
        return cloudconvert.Job.create(
            {
                "tasks": {
                    'upload-my-file': {
                        'operation': 'import/upload'
                    },
                    'convert-my-file': {
                        'operation': 'convert',
                        'input': 'upload-my-file',
                        'output_format': f'{convert_format}',
                        'some_other_option': 'value'
                    },
                    'export-my-file': {
                        'operation': 'export/url',
                        'input': 'convert-my-file'
                    }
                }
            }
        )

    def upload_file(self, job, file_name):
        upload_task_id = job['tasks'][0]['id']
        upload_task = cloudconvert.Task.find(id=upload_task_id)
        cloudconvert.Task.upload(
            file_name=f"temporary/{file_name}", task=upload_task)
        cloudconvert.Task.find(id=upload_task_id)

    def export_file(self, job, file_name):
        exported_url_task_id = job['tasks'][2]['id']
        res = cloudconvert.Task.wait(
            id=exported_url_task_id)  # Wait for job completion
        file = res.get("result").get("files")[0]
        cloudconvert.download(
            filename=f"finished/{file_name}", url=file['url'])


class TelegramBot():
    def __init__(self):
        TGBOT_TOKEN = os.getenv("TGBOT_TOKEN")
        self.support_formats = [
            'pdf',
            'docx',
            'jpg',
            'png'
        ]
        self.updater = Updater(token=TGBOT_TOKEN, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self.dispatcher.add_handler(
            MessageHandler(
                Filters.document,
                self.trigger))
        self.updater.dispatcher.add_handler(
            CallbackQueryHandler(self.start_convert))
        self.dispatcher.add_handler(CommandHandler('help', self.help))
        self.convert = Convert()
        self.updater.start_polling()
        self.updater.idle()

    def help(self, update, context):
        update.message.reply_text(text=help_text)

    def trigger(self, update, context):
        # writing to a custom file
        update.message.reply_text(text=recieve_text)
        file_name = update.message.document.file_name
        with open(f"temporary/{file_name}", 'wb') as f:
            context.bot.get_file(update.message.document).download(out=f)
        update.message.reply_text(text=convert_type_text, reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f'{support_format}', callback_data=f'{file_name}:{support_format}'
                    ) for support_format in self.support_formats
                ]
            ]
        )
        )

    def start_convert(self, update, context):
        cbdata = update.callback_query.data
        file_name = cbdata.split(':')[0]
        convert_format = cbdata.split(':')[1]
        update.callback_query.message.reply_text(
            text=converting_text.format(convert_format))
        # create job
        job = self.convert.create_job(convert_format)
        # upload file
        self.convert.upload_file(job, file_name)
        # export file
        self.convert.export_file(job, file_name)

        doc_file = open(f"finished/{file_name}", "rb")
        update.callback_query.message.reply_document(
            quote="owo",
            document=doc_file,
            filename=f"{file_name}.{convert_format}",
        )


if __name__ == '__main__':
    telegram = TelegramBot()
