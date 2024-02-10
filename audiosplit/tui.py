import os
import sys
from typing import Optional

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Placeholder

import audiosplit.cut as cut
from audiosplit.cut import BADFORMAT


class TableApp(App):
    tracklist = ""
    input_mp3_filename = ""

    def set_data(
        self,
        tracklist: str,
        input_mp3_fileame: str,
        output_dir: str = "output",
    ) -> None:
        self.tracklist = tracklist
        self.input_mp3_filename = input_mp3_fileame
        self.output_dir = os.path.join(os.path.dirname(input_mp3_fileame), output_dir)

    def compose(self) -> ComposeResult:
        self.title = "AudioSplit"
        # yield Horizontal(Static("Input file:"), Static(self.input_file))
        self.tl = Placeholder(f"Tracklist:{self.tracklist}", name="tracklist")
        self.run_button = Button("Run", name="run_button")

        self.tl.styles.width = "100%"
        self.tl.styles.height = "90%"
        self.tl.styles.content_align = "left", "top"
        self.regexinput = Input(
            placeholder="Type regex and press Enter or Click 'Update'",
            name="regex_input",
            value=cut.STARTPATTERN,
        )
        # self.update_button = Button("Update", name="update_button")
        self.table = DataTable()
        yield Vertical(
            Horizontal(
                Vertical(self.tl, self.run_button),
                Vertical(self.regexinput, self.table),
            )
        )

    @on(Button.Pressed)
    async def cut_file(self, _: Button.Pressed) -> None:
        regex = self.query_one(Input).value
        start_times, track_names = cut.parse_tracklist(self.tracklist, regex)
        # Calculate the end times
        end_times = start_times[1:] + ["EOF"]

        cut.process_file_list(
            self.input_mp3_filename,
            start_times,
            end_times,
            track_names,
            self.output_dir,
        )
        # exit(0)

        sys.exit(0)

        # except BADFORMAT:
        # self.tl.value = "Done!"

    def on_mount(self) -> None:
        # self.query_one(Input).render_str("dud")  # ; = cut.STARTPATTERN

        self.query_one(Input).focus()
        self.query_one(DataTable).add_column("No")
        self.query_one(DataTable).add_column("Trackname")
        self.query_one(DataTable).add_column("Length")

    async def on_input_changed(self, _) -> None:
        # if message.key == "enter":
        regex = self.query_one(Input).value
        self.update_table(regex)
        self.query_one(DataTable).render()

    # async def on_button_click(self, message: Button.Pressed) -> None:
    #     if message.sender.name == "update_button":
    #         regex = self.query_one(Input, name="regex_input").text
    #         self.update_table(regex)

    def update_table(self, regex: str) -> None:
        table = self.query_one(DataTable)
        try:
            rows = calc_table(regex, self.tracklist)
        except BADFORMAT:
            table.clear()
            table.add_row("", "Tracklist format / regex is not correct.", "")
            return
        table.clear()
        for idx, (start, track_name) in rows:
            table.add_row(
                str(idx + 1), start, track_name
            )  # Added idx + 1 to start the No from 1 instead of 0


def calc_table(regex: str, text: str):
    a, b = cut.parse_tracklist(text, regex)
    return list(enumerate(zip(a, b)))


def tui_main():
    (_, tracklist_in, input_file) = cut.argparsing()
    app = TableApp()
    app.set_data(tracklist_in, input_file)
    app.run()


if __name__ == "__main__":
    tui_main()
