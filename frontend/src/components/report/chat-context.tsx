"use client";
import { createContext, useContext } from "react";
import type { Finding } from "@/lib/report-types";
export const ChatContext = createContext<{
  me?: string;
  meName?: string;
  ask?: (finding?: Finding) => void;
}>({});
export const useChatContext = () => useContext(ChatContext);
