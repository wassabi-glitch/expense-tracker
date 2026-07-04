import assert from "node:assert/strict";
import test from "node:test";

import { localizeApiError } from "./errorMessages.js";

function t(key, options = {}) {
  return options.defaultValue || key;
}

test("localizes isolated project wallet funding errors", () => {
  assert.equal(
    localizeApiError("projects.wallet_funding_required", t),
    "This wallet has not funded the isolated project. Choose a project-funded wallet or top up the project first.",
  );
  assert.equal(
    localizeApiError("projects.wallet_funding_exceeded", t),
    "This wallet does not have enough remaining project funding. Choose another project wallet, split the payment, or top up first.",
  );
});
