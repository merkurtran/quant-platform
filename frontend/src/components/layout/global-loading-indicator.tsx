"use client";

import { useIsFetching, useIsMutating } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";

export function GlobalLoadingIndicator() {
  const requestCount = useIsFetching() + useIsMutating();
  const isBusy = requestCount > 0;

  return (
    <AnimatePresence>
      {isBusy && (
        <motion.div
          className="pointer-events-none fixed inset-x-0 top-12 z-[100] h-0.5 overflow-hidden bg-primary/15"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { duration: 0.1 } }}
          transition={{ delay: 1, duration: 0.12 }}
        >
          <motion.div
            className="h-full w-1/3 bg-primary"
            animate={{ x: ["-100%", "300%"] }}
            transition={{ duration: 1.1, ease: "easeInOut", repeat: Infinity }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
