import sys

if __name__ == "__main__":
    if "--esptool-helper" in sys.argv:
        import esptool
        marker = sys.argv.index("--esptool-helper")
        esptool.main(sys.argv[marker + 1:])
    else:
        from hackman_layershot.main import main
        main()
