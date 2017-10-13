##Translations

###New

1.  Create a new translation file:

    ```
    meson translation-build
    ninja -C translation-build seneca-pot
    mv po/seneca.pot po/$lang.po
    ```

    Where `$lang` is the language code of the target language.

2.  Add the language code to the LINGUAS file in alphabetical order.



###Update

1.  Regenerate translation files.

    ```
    meson translation-build
    ninja -C translation-build seneca-update-po
    ```

2. Modify the target language file.
