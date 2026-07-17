import re

with open('frontend/src/pages/settings.tsx', 'r') as f:
    content = f.read()

# Add Appearance card
appearance_card = """
      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-mono flex items-center gap-2">
            <Sun className="w-4 h-4 text-muted-foreground" />
            Appearance
          </CardTitle>
          <CardDescription className="font-mono text-xs">
            Choose your preferred theme for the VIT Network interface.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button
              variant={theme === "light" ? "default" : "outline"}
              size="sm"
              className="flex-1 font-mono gap-2"
              onClick={() => setTheme("light")}
            >
              <Sun className="w-4 h-4" /> Light
            </Button>
            <Button
              variant={theme === "dark" ? "default" : "outline"}
              size="sm"
              className="flex-1 font-mono gap-2"
              onClick={() => setTheme("dark")}
            >
              <Moon className="w-4 h-4" /> Dark
            </Button>
          </div>
        </CardContent>
      </Card>
"""

# Insert after the Profile card (or at the end of the top section)
content = content.replace('{/* 2FA */}', appearance_card + '\n      {/* 2FA */}')

with open('frontend/src/pages/settings.tsx', 'w') as f:
    f.write(content)
