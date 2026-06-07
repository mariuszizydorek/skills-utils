import ora from "ora";

export type SyncAction = "remove" | "install" | "update";

export interface SyncProgressReporter {
  begin(total: number, message?: string): void;
  removing(name: string, index: number, total: number): void;
  downloading(name: string, relPath: string, fileIndex: number, fileTotal: number): void;
  installing(name: string): void;
  linking(name: string): void;
}

export class OraSyncProgress implements SyncProgressReporter {
  private spinner = ora("Applying changes…").start();
  private total = 1;
  private completed = 0;

  begin(total: number, message = "Applying changes"): void {
    this.total = Math.max(total, 1);
    this.completed = 0;
    this.spinner.text = `${message} (0/${this.total})`;
  }

  private pct(): string {
    const percent = Math.min(100, Math.round((this.completed / this.total) * 100));
    return `${percent}%`;
  }

  removing(name: string, index: number, total: number): void {
    this.completed += 1;
    this.spinner.text = `[${this.pct()}] Removing ${name} (${index}/${total})`;
  }

  downloading(name: string, relPath: string, fileIndex: number, fileTotal: number): void {
    this.spinner.text = `[${this.pct()}] Downloading ${name} — ${relPath} (${fileIndex}/${fileTotal})`;
  }

  installing(name: string): void {
    this.completed += 1;
    this.spinner.text = `[${this.pct()}] Installing ${name}`;
  }

  linking(name: string): void {
    this.spinner.text = `[${this.pct()}] Linking ${name}`;
  }

  succeed(message: string): void {
    this.spinner.succeed(message);
  }

  fail(message: string): void {
    this.spinner.fail(message);
  }
}
