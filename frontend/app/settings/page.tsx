"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function SettingsPage() {
  return (
    <main className="shell py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-normal">Settings</h1>
        <p className="mt-2 text-muted-foreground">Tune the library defaults that shape how your workspace feels day to day.</p>
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Library preferences</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <label className="grid gap-2 text-sm font-medium">
              Default sort
              <select className="h-10 rounded-md border bg-white px-3 text-sm">
                <option>Newest first</option>
                <option>Oldest first</option>
                <option>Recently edited</option>
                <option>Title A-Z</option>
              </select>
            </label>
            <label className="grid gap-2 text-sm font-medium">
              Default library view
              <select className="h-10 rounded-md border bg-white px-3 text-sm">
                <option>Card view</option>
                <option>List view</option>
              </select>
            </label>
            <label className="flex items-center justify-between rounded-lg border bg-white px-4 py-3 text-sm font-medium">
              Automatic organization
              <input type="checkbox" defaultChecked className="size-4" />
            </label>
            <label className="flex items-center justify-between rounded-lg border bg-white px-4 py-3 text-sm font-medium">
              Open uploaded document after processing
              <input type="checkbox" defaultChecked className="size-4" />
            </label>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <label className="grid gap-2 text-sm font-medium">
              Display name
              <Input placeholder="DocuParse user" />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              Email
              <Input type="email" placeholder="you@company.com" />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              Workspace label
              <Input placeholder="Operations, Finance, School, Personal" />
            </label>
            <div className="rounded-lg border bg-white p-4 text-sm text-muted-foreground">
              Auth is still a lightweight product shell here, but this page gives the app a proper home for account and workflow defaults.
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
