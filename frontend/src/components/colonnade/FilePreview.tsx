import type { SourceFile } from './sourceFiles';

/** One document tile inside the folder card, and inside the expanded grid. */
export function FilePreview({ file }: { file: SourceFile }) {
  return (
    <span className="flex h-full w-full flex-col gap-1.5 bg-white p-2.5">
      <span
        className="inline-flex w-fit items-center rounded-[3px] px-1 py-0.5 text-[7px] font-semibold
          uppercase leading-none tracking-[0.06em] text-white"
        style={{ background: file.tint }}
      >
        {file.source}
      </span>
      <span className="text-[8px] font-medium leading-[1.25] text-ink/80">{file.title}</span>
      {/* Ruled lines stand in for body copy at a size where real text would be
        * illegible anyway -- three fixed widths so the tile reads as a
        * document rather than a placeholder block. */}
      <span aria-hidden="true" className="mt-auto flex flex-col gap-1">
        <span className="block h-px w-full bg-ink/10" />
        <span className="block h-px w-full bg-ink/10" />
        <span className="block h-px w-2/3 bg-ink/10" />
      </span>
    </span>
  );
}
