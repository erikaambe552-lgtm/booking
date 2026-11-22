import os

from django.conf import settings
from django.core.management.base import CommandError
from daphne.management.commands.runserver import Command as DaphneRunserverCommand


class Command(DaphneRunserverCommand):
    help = "Starts the ASGI server (four worker processes by default)."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--workers",
            type=int,
            default=settings.RUNSERVER_WORKERS,
            help="Number of ASGI worker processes (default: %(default)s).",
        )

    def handle(self, *args, **options):
        self.workers = options["workers"]
        if self.workers < 1:
            raise CommandError("--workers must be at least 1.")
        if self.workers > 1:
            if not options["use_asgi"]:
                raise CommandError("Multiple workers require the ASGI server.")
            if options["use_reloader"]:
                options["use_reloader"] = False
                self.stdout.write(
                    "Autoreload is disabled with multiple workers; use --workers 1 for autoreload."
                )
            if not settings.REDIS_URL:
                self.stderr.write(
                    self.style.WARNING(
                        "REDIS_URL is unset; WebSocket events will not be shared "
                        "between worker processes. Configure Redis, e.g. "
                        "redis://127.0.0.1:6380/0."
                    )
                )
        return super().handle(*args, **options)

    def inner_run(self, *args, **options):
        if self.workers == 1:
            return super().inner_run(*args, **options)

        self.stdout.write("Performing system checks...\n\n")
        self.check(display_num_errors=True)
        self.check_migrations()
        self.stdout.write(
            f"Starting ASGI/Uvicorn server at http://{self.addr}:{self.port}/ "
            f"with {self.workers} workers.\n"
            "Quit the server with CTRL-BREAK.\n"
        )

        import uvicorn

        if os.name != "nt":
            uvicorn.run(
                "config.asgi:application",
                host=self.addr,
                port=int(self.port),
                workers=self.workers,
                log_level="info",
            )
            return

        from uvicorn.supervisors.multiprocess import Multiprocess, Process

        config = uvicorn.Config(
            "config.asgi:application",
            host=self.addr,
            port=int(self.port),
            workers=self.workers,
            log_level="info",
        )
        sockets = [config.bind_socket()]

        class SequentialWindowsMultiprocess(Multiprocess):
            def init_processes(self):
                for _ in range(self.processes_num):
                    process = Process(self.config, self.sockets)
                    process.start()
                    self.processes.append(process)
                    if process.wait_until_ready(timeout=30, should_exit=self.should_exit):
                        continue

                    if process.process.is_alive():
                        process.kill()
                    process.join()
                    self.terminate_all()
                    self.join_all()
                    raise RuntimeError(
                        f"Uvicorn worker {process.pid} failed to become ready."
                    )

        SequentialWindowsMultiprocess(
            config=config,
            sockets=sockets,
        ).run()
