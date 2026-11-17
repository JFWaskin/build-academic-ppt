import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const extensionDir = dirname(fileURLToPath(import.meta.url));
const packageRoot = resolve(extensionDir, "../..");
const skillsDir = resolve(packageRoot, "skills");

/**
 * build-academic-ppt for pi
 *
 * The skill is plain files, so registering the skills directory is all that
 * is needed. The QA protocol inside the skill asks for a reviewer that did
 * not write the deck -- pi's subagent facility covers that.
 */
export default function buildAcademicPptPiExtension(pi: ExtensionAPI) {
	pi.on("resources_discover", async () => ({
		skillPaths: [skillsDir],
	}));
}
