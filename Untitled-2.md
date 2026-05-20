good. now we will get back to it later. currently let's solve the previous issue : `
> dukan@2.0.1 build:frontend
> tsc --noEmit && vite build

rolldown-vite v7.1.14 building for production...
[baseline-browser-mapping] The data in this module is over two months old.  To ensure accurate Baseline data, please update: `npm i baseline-browser-mapping@latest -D`
transforming (3102) src\components\InvoiceSettingsModal.tsxBrowserslist: browsers data (caniuse-lite) is 6 months old. Please run:
  npx update-browserslist-db@latest
  Why you should do it regularly: https://github.com/browserslist/update-db#readme
✓ 3108 modules transformed.
✗ Build failed in 7.00s
error during build:
Build failed with 1 error:

[plugin vite:react-babel] W:/workplace-1/Dukan-Django/src/pages/InventoryPage.tsx:488:4
SyntaxError: W:\workplace-1\Dukan-Django\src\pages\InventoryPage.tsx: Unexpected reserved word 'await'. (488:4)

  486 |       handleFinalPrint();
  487 |     }, 100);
> 488 |     await printWithCleanHeaders(templateBackgroundStyle);
      |     ^
  489 |   };
  490 |
  491 |   return (
    at constructor (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:367:19)
    at TypeScriptParserMixin.raise (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:6624:19)
    at TypeScriptParserMixin.checkReservedWord (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:12305:12)
    at TypeScriptParserMixin.checkReservedWord (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:9369:13)
    at TypeScriptParserMixin.parseIdentifierName (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:12285:12)
    at TypeScriptParserMixin.parseIdentifier (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:12255:23)
    at TypeScriptParserMixin.parseExprAtom (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:11482:27)
    at TypeScriptParserMixin.parseExprAtom (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:4793:20)
    at TypeScriptParserMixin.parseExprSubscripts (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:11145:23)
    at TypeScriptParserMixin.parseUpdate (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:11130:21)
    at TypeScriptParserMixin.parseMaybeUnary (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:11110:23)
    at TypeScriptParserMixin.parseMaybeUnary (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:9890:18)
    at TypeScriptParserMixin.parseMaybeUnaryOrPrivate (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:10963:61)
    at TypeScriptParserMixin.parseExprOps (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:10968:23)
    at TypeScriptParserMixin.parseMaybeConditional (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:10945:23)
    at TypeScriptParserMixin.parseMaybeAssign (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:10895:21)
    at TypeScriptParserMixin.parseMaybeAssign (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:9839:20)
    at TypeScriptParserMixin.parseExpressionBase (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:10848:23)
    at W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:10844:39
    at TypeScriptParserMixin.allowInAnd (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:12495:16)
    at TypeScriptParserMixin.parseExpression (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:10844:17)
    at TypeScriptParserMixin.parseStatementContent (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:12971:23)
    at TypeScriptParserMixin.parseStatementContent (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:9569:18)
    at TypeScriptParserMixin.parseStatementLike (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:12843:17)
    at TypeScriptParserMixin.parseStatementListItem (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:12823:17)
    at TypeScriptParserMixin.parseBlockOrModuleBlockBody (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:13392:61)
    at TypeScriptParserMixin.parseBlockBody (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:13385:10)
    at TypeScriptParserMixin.parseBlock (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:13373:10)
    at TypeScriptParserMixin.parseFunctionBody (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:12174:24)
    at TypeScriptParserMixin.parseArrowExpression (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:12149:10)
    at TypeScriptParserMixin.parseParenAndDistinguishExpression (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:11759:12)
    at TypeScriptParserMixin.parseExprAtom (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:11395:23)
    at TypeScriptParserMixin.parseExprAtom (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:4793:20)
    at TypeScriptParserMixin.parseExprSubscripts (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:11145:23)
    at TypeScriptParserMixin.parseUpdate (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:11130:21)
    at TypeScriptParserMixin.parseMaybeUnary (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:11110:23)
    at TypeScriptParserMixin.parseMaybeUnary (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:9890:18)
    at TypeScriptParserMixin.parseMaybeUnaryOrPrivate (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:10963:61)
    at TypeScriptParserMixin.parseExprOps (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:10968:23)
    at TypeScriptParserMixin.parseMaybeConditional (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:10945:23)
    at TypeScriptParserMixin.parseMaybeAssign (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:10895:21)
    at TypeScriptParserMixin.parseMaybeAssign (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:9839:20)
    at W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:10864:39
    at TypeScriptParserMixin.allowInAnd (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:12495:16)
    at TypeScriptParserMixin.parseMaybeAssignAllowIn (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:10864:17)
    at TypeScriptParserMixin.parseVar (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:13460:91)
    at TypeScriptParserMixin.parseVarStatement (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:13306:10)
    at TypeScriptParserMixin.parseVarStatement (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:9469:31)
    at TypeScriptParserMixin.parseStatementContent (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:12927:23)
    at TypeScriptParserMixin.parseStatementContent (W:\workplace-1\Dukan-Django\node_modules\@babel\parser\lib\index.js:9569:18)
    at normalizeErrors (file:///W:/workplace-1/Dukan-Django/node_modules/rolldown/dist/shared/src-DkvlJJsC.mjs:2157:18)
    at handleOutputErrors (file:///W:/workplace-1/Dukan-Django/node_modules/rolldown/dist/shared/src-DkvlJJsC.mjs:2892:34)
    at transformToRollupOutput (file:///W:/workplace-1/Dukan-Django/node_modules/rolldown/dist/shared/src-DkvlJJsC.mjs:2886:2)
    at RolldownBuild.write (file:///W:/workplace-1/Dukan-Django/node_modules/rolldown/dist/shared/src-DkvlJJsC.mjs:4093:10)
    at async buildEnvironment (file:///W:/workplace-1/Dukan-Django/node_modules/vite/dist/node/chunks/dep-ySrR9pW8.js:33173:64)
    at async Object.build (file:///W:/workplace-1/Dukan-Django/node_modules/vite/dist/node/chunks/dep-ySrR9pW8.js:33577:19)
    at async Object.buildApp (file:///W:/workplace-1/Dukan-Django/node_modules/vite/dist/node/chunks/dep-ySrR9pW8.js:33574:153)
    at async CAC.<anonymous> (file:///W:/workplace-1/Dukan-Django/node_modules/vite/dist/node/cli.js:641:3)
[SETTINGS] Configuration loaded from: remote
[SETTINGS] SENDGRID_API_KEY: True
[SETTINGS] ADMIN_EMAIL: info@codeit-technologies.com
Deleting 'D-nobg.png'
Deleting 'Icon.ico'
Deleting 'index.html'
Deleting 'admin\css\autocomplete.css'
Deleting 'admin\css\base.css'
Deleting 'admin\css\changelists.css'
Deleting 'admin\css\dark_mode.css'
Deleting 'admin\css\dashboard.css'
Deleting 'admin\css\forms.css'
Deleting 'admin\css\login.css'
Deleting 'admin\css\nav_sidebar.css'
Deleting 'admin\css\responsive.css'
Deleting 'admin\css\responsive_rtl.css'
Deleting 'admin\css\rtl.css'
Deleting 'admin\css\widgets.css'
Deleting 'admin\css\vendor\select2\LICENSE-SELECT2.md'
Deleting 'admin\css\vendor\select2\select2.css'
Deleting 'admin\css\vendor\select2\select2.min.css'
Deleting 'admin\img\calendar-icons.svg'
Deleting 'admin\img\icon-addlink.svg'
Deleting 'admin\img\icon-alert.svg'
Deleting 'admin\img\icon-calendar.svg'
Deleting 'admin\img\icon-changelink.svg'
Deleting 'admin\img\icon-clock.svg'` i had got this error while run build and collectstatic on the issue of that last we were working on.. printing the inventory