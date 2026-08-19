/* Renders both routes through Vite's SSR pipeline. Effects do not run here,
 * so this validates imports, JSX and the initial (loading) render of every
 * component — it does not validate Cytoscape or live data. */
import { createServer } from 'vite';
import { renderToString } from 'react-dom/server';
import React from 'react';
import { StaticRouter } from 'react-router';

const vite = await createServer({
  server: { middlewareMode: true },
  appType: 'custom',
  logLevel: 'error',
});

let failed = 0;
try {
  const { default: App } = await vite.ssrLoadModule('/src/App.tsx');
  for (const path of ['/', '/dashboard']) {
    try {
      const html = renderToString(
        React.createElement(StaticRouter, { location: path }, React.createElement(App)),
      );
      const len = html.length;
      if (len < 200) throw new Error(`suspiciously short render (${len} chars)`);
      console.log(`  PASS  ${path.padEnd(11)} rendered ${len} chars`);
      const probe = path === '/' ? 'Theia' : 'Ask the company brain';
      console.log(`        contains ${JSON.stringify(probe)}: ${html.includes(probe)}`);
    } catch (e) {
      failed++;
      console.log(`  FAIL  ${path} -> ${e.message}`);
    }
  }
} catch (e) {
  failed++;
  console.log(`  FAIL  module load -> ${e.message}`);
}

await vite.close();
process.exit(failed ? 1 : 0);
