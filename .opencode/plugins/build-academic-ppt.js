/**
 * build-academic-ppt for OpenCode.ai
 *
 * Registers the skills directory so OpenCode discovers the skill without
 * manual symlinks or config edits. The skill itself is plain files, so
 * there is nothing else to inject.
 */

import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const skillDir = path.resolve(__dirname, '../../skills');

export const buildAcademicPpt = {
  /**
   * Register the skills directory with the live config.
   */
  config: async (config) => {
    config.skills = config.skills || {};
    config.skills.paths = config.skills.paths || [];
    if (!config.skills.paths.includes(skillDir)) {
      config.skills.paths.push(skillDir);
    }
  },
};

export default buildAcademicPpt;
