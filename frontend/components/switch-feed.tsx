"use client";

import { useEffect, useRef } from "react";
import { Sign } from "@/components/sign";
import { TAG_SIGN, type FeedMessage } from "@/lib/radar";

export function SwitchFeed({ feed }: { feed: FeedMessage[] }) {
  const ref = useRef<HTMLOListElement>(null);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [feed.length]);

  if (feed.length === 0) {
    return <p className="text-dim">Messages appear here as agents talk in the rooms.</p>;
  }

  return (
    <ol ref={ref} className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
      {feed.map((message) => (
        <li key={message.id} className="text-sm">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-medium">{message.sender}</span>
            <span className="text-dim">in {message.room}</span>
            {message.tag && (
              <Sign kind={TAG_SIGN[message.tag] ?? "plain"} className="!border-1 text-sm">
                {message.tag}
              </Sign>
            )}
          </div>
          <pre className="mt-1 font-mono text-[13px] leading-relaxed break-words whitespace-pre-wrap">
            {message.face && <span className="mr-2 text-dim">{message.face}</span>}
            {message.tag ? message.text.replace(`${message.tag}\n`, "") : message.text}
          </pre>
        </li>
      ))}
    </ol>
  );
}
